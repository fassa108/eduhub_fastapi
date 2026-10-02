import io
import zipfile

from fastapi import UploadFile

from app.config import settings
from app.extraction import EXTRACTEURS

SIGNATURE_ZIP = b"PK\x03\x04"
SIGNATURES = {"pdf": b"%PDF", "docx": SIGNATURE_ZIP, "pptx": SIGNATURE_ZIP}


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


class ArchiveTropVolumineuse(ErreurValidation):
    status_code = 413


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

    if signature == SIGNATURE_ZIP:
        _verifier_archive(nom, contenu)

    return contenu


def _verifier_archive(nom: str, contenu: bytes) -> None:
    """DOCX et PPTX sont des ZIP : on borne leur taille une fois décompressés."""
    try:
        with zipfile.ZipFile(io.BytesIO(contenu)) as archive:
            taille = sum(f.file_size for f in archive.infolist())
    except zipfile.BadZipFile as e:
        raise ContenuInvalide(f"'{nom}' est corrompu") from e
    if taille > settings.taille_decompressee_max_mo * 1024 * 1024:
        raise ArchiveTropVolumineuse(
            f"'{nom}' dépasse {settings.taille_decompressee_max_mo} Mo une fois décompressé"
        )


def valider_longueur_texte(texte: str) -> None:
    if len(texte) > settings.max_chars:
        raise TexteTropLong(
            f"Texte trop long ({len(texte)} caractères, "
            f"maximum {settings.max_chars}). Sélectionnez moins de ressources."
        )