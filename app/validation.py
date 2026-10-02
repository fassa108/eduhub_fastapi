from fastapi import UploadFile

from app.config import settings
from app.extraction import EXTRACTEURS

SIGNATURES = {"pdf": b"%PDF", "docx": b"PK\x03\x04", "pptx": b"PK\x03\x04"}


class ErreurValidation(Exception):
    status_code = 422


class FormatInvalide(ErreurValidation):
    status_code = 415


class TropDeFichiers(ErreurValidation):
    status_code = 413


class FichierTropVolumineux(ErreurValidation):
    status_code = 413


class TexteTropLong(ErreurValidation):
    status_code = 413


class ContenuInvalide(ErreurValidation):
    status_code = 422


def extension_de(nom: str) -> str:
    return nom.lower().rsplit(".", 1)[-1] if "." in nom else ""


def valider_nombre_fichiers(fichiers: list[UploadFile]) -> None:
    if len(fichiers) > settings.nb_fichiers_max:
        raise TropDeFichiers(f"Maximum {settings.nb_fichiers_max} fichiers")


def lire_fichier_valide(fichier: UploadFile) -> bytes:
    """Contrôle l'extension, la taille et la signature, puis renvoie le contenu."""
    nom = fichier.filename or ""
    extension = extension_de(nom)

    if extension not in EXTRACTEURS:
        raise FormatInvalide(f"Format non supporté : '{extension}'")

    limite = settings.taille_max_mo * 1024 * 1024
    contenu = fichier.file.read(limite + 1)
    if len(contenu) > limite:
        raise FichierTropVolumineux(
            f"'{nom}' dépasse {settings.taille_max_mo} Mo"
        )

    signature = SIGNATURES.get(extension)
    if signature and not contenu.startswith(signature):
        raise ContenuInvalide(f"'{nom}' n'est pas un vrai fichier {extension}")

    return contenu


def valider_longueur_texte(texte: str) -> None:
    if len(texte) > settings.max_chars:
        raise TexteTropLong(
            f"Texte trop long ({len(texte)} caractères, "
            f"maximum {settings.max_chars}). Sélectionnez moins de ressources."
        )