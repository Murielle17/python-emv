import sys
import logging
import smartcard
import textwrap
import click
from terminaltables import SingleTable
import emv
from emv.card import Card
from emv.protocol.data import Tag, render_element
from emv.protocol.structures import TLV
from emv.protocol.response import ErrorResponse
from emv.exc import InvalidPINException, MissingAppException, CAPError
from emv.util import format_bytes

# Définition des niveaux de log
LOG_LEVELS = {"info": logging.INFO, "debug": logging.DEBUG, "warn": logging.WARN}


def as_table(tlv, title=None, redact=False):
    """Convertit une structure TLV en table affichable."""
    if not isinstance(tlv, TLV):
        return ""

    rows = [["Tag", "Name", "Value"]]
    for tag, value in tlv.items():
        rows.append([
            format_bytes(tag.id),
            tag.name or "",
            "\n".join(textwrap.wrap(render_element(tag, value, redact=redact), 80)),
        ])

    table = SingleTable(rows)
    if title:
        table.title = title
    return table.table


def get_reader(reader_index):
    """Récupère un lecteur de cartes basé sur son index."""
    try:
        reader = smartcard.System.readers()[reader_index]
        return Card(reader.createConnection())
    except IndexError:
        click.secho("Reader or card not found", fg="red")
        sys.exit(2)


def run():
    """Point d'entrée principal de la ligne de commande."""
    cli(obj={})


@click.group(
    help="""Outil pour interagir avec les cartes EMV.

Bien que cet outil ait été testé, il peut endommager ou bloquer votre carte.
Utilisez-le avec précaution.
"""
)
@click.option("--reader", "-r", type=int, default=0, help="Index du lecteur à utiliser (par défaut 0)")
@click.option("--pin", "-p", type=str, help="PIN. Attention, il peut être visible dans les processus système.")
@click.option("--loglevel", "-l", type=str, default="warn", help="Niveau de log")
@click.option("--redact/--no-redact", default=False, help="Masquer les données sensibles (pas totalement sécurisé).")
@click.pass_context
def cli(ctx, reader, pin, loglevel, redact):
    logging.basicConfig(level=LOG_LEVELS.get(loglevel, logging.WARN))
    ctx.obj.update({"pin": pin, "reader": reader, "redact": redact})


@cli.command(help="Afficher la version de l'outil EMV.")
def version():
    click.echo(emv.__version__)


@cli.command(help="Lister les lecteurs de cartes disponibles.")
def readers():
    click.secho("Lecteurs disponibles :\n", bold=True)
    for index, reader in enumerate(smartcard.System.readers()):
        click.echo(f"{index}: {reader}")


def render_app(card, df, redact):
    """Affiche les données d'une application spécifique."""
    try:
        data = card.select_application(df).data
        click.echo(as_table(data.get(Tag.FCI, {}).get(Tag.FCI_PROP, {}), "FCI Proprietary Data", redact))
        for sfi in range(1, 31):
            for record in range(1, 16):
                try:
                    rec = card.read_record(record, sfi=sfi).data
                    if Tag.RECORD in rec:
                        click.echo(as_table(rec[Tag.RECORD], f"File: {sfi},{record}", redact))
                except ErrorResponse:
                    continue
    except MissingAppException:
        click.secho(f"{df} non disponible (normal sur certaines cartes).", fg="yellow")


@cli.command(help="Afficher les informations sur la carte.")
@click.pass_context
def info(ctx):
    redact = ctx.obj["redact"]
    card = get_reader(ctx.obj["reader"])
    click.secho("Applications sur la carte :\n", bold=True)

    for index, (title, df) in enumerate([
        ("1PAY.SYS.DDF01 (Paiements par puce)", "1PAY.SYS.DDF01"),
        ("2PAY.SYS.DDF01 (Paiements sans contact)", "2PAY.SYS.DDF01")
    ]):
        click.secho(f"\n{index + 1}. {title}", bold=True)
        render_app(card, df, redact)

    apps = card.list_applications()
    for app in apps:
        label = render_element(Tag.APP_LABEL, app.get(Tag.APP_LABEL, ""))
        df_name = render_element(Tag.DF, app.get(Tag.ADF_NAME, ""))
        click.secho(f"\nApplication : {label}, DF Name : {df_name}", bold=True)
        render_app(card, app[Tag.ADF_NAME], redact)

    click.secho("\nMétadonnées de la carte :", bold=True)
    try:
        metadata = card.get_metadata()
        table = SingleTable(metadata.items())
        table.inner_heading_row_border = False
        click.echo(table.table)
    except ErrorResponse as e:
        click.secho(f"Impossible de récupérer les métadonnées : {e}", fg="yellow")


@cli.command(help="[!] Effectuer une authentification EMV CAP.")
@click.option("--challenge", "-c", help="Numéro de compte ou défi.")
@click.option("--amount", "-a", help="Montant.")
@click.pass_context
def cap(ctx, challenge, amount):
    pin = ctx.obj.get("pin")
    if not pin:
        click.secho("Le PIN est requis.", fg="red")
        sys.exit(2)

    if amount and not challenge:
        click.secho("Un défi (numéro de compte) est requis avec un montant.", fg="red")
        sys.exit(3)

    card = get_reader(ctx.obj["reader"])
    try:
        result = card.generate_cap_value(pin, challenge=challenge, value=amount)
        click.echo(result)
    except InvalidPINException:
        click.secho("PIN invalide.", fg="red")
    except CAPError as e:
        click.secho(f"Erreur dans la génération CAP : {e}", fg="red")


@cli.command(help="[!] Lister les applications nommées sur la carte.")
@click.pass_context
def listapps(ctx):
    card = get_reader(ctx.obj["reader"])
    apps = card.list_applications()
    rows = [["Index", "Label", "ADF"]]
    for i, app in enumerate(apps):
        rows.append([
            i,
            render_element(Tag.APP_LABEL, app.get(Tag.APP_LABEL, "")),
            render_element(Tag.ADF_NAME, app.get(Tag.ADF_NAME, ""))
        ])
    table = SingleTable(rows)
    table.title = "Applications"
    click.echo(table.table)


@cli.command(help="[!] Vérifier le PIN.")
@click.argument("app_index", type=int)
@click.pass_context
def verifypin(ctx, app_index):
    pin = ctx.obj.get("pin")
    if not pin:
        click.secho("Le PIN est requis.", fg="red")
        sys.exit(2)

    card = get_reader(ctx.obj["reader"])
    apps = card.list_applications()
    app = apps[app_index]
    card.select_application(app[Tag.ADF_NAME])
    card.verify_pin(pin)
    click.secho("PIN vérifié avec succès.", fg="green")
