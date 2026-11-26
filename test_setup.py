#!/usr/bin/env python
"""
Script de test de configuration pour Keck3.
Vérifie que tous les dépendances et configurations sont correctes.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Teste que tous les imports essentiels fonctionnent."""
    print("Testing imports...")
    try:
        import serial
        print("  ✓ pyserial")
    except ImportError:
        print("  ✗ pyserial (installer: pip install pyserial)")
        return False

    try:
        import requests
        print("  ✓ requests")
    except ImportError:
        print("  ✗ requests (installer: pip install requests)")
        return False

    try:
        import dotenv
        print("  ✓ python-dotenv")
    except ImportError:
        print("  ✗ python-dotenv (installer: pip install python-dotenv)")
        return False

    # Imports internes
    try:
        from core.logger import setup_logger
        print("  ✓ core.logger")
    except ImportError as e:
        print(f"  ✗ core.logger: {e}")
        return False

    try:
        from core.serial_reader import SerialReader
        print("  ✓ core.serial_reader")
    except ImportError as e:
        print(f"  ✗ core.serial_reader: {e}")
        return False

    try:
        from api.client import OpenProdAPIClient
        print("  ✓ api.client")
    except ImportError as e:
        print(f"  ✗ api.client: {e}")
        return False

    try:
        from api.models import DataParser
        print("  ✓ api.models")
    except ImportError as e:
        print(f"  ✗ api.models: {e}")
        return False

    return True

def test_directories():
    """Teste que les répertoires existent."""
    print("\nTesting directories...")
    base = Path(__file__).parent
    dirs = [base / "core", base / "api", base / "labels", base / "logs", base / "data"]

    for d in dirs:
        if d.exists():
            print(f"  ✓ {d.name}")
        else:
            print(f"  ✗ {d.name} (sera créé)")

    return True

def test_config():
    """Teste la configuration."""
    print("\nTesting configuration...")

    try:
        from config import (
            OPEN_PROD_BASE_URL,
            OPEN_PROD_DB,
            OPEN_PROD_API_KEY,
            OPEN_PROD_MAPPING_FILE,
            SERIAL_PORT,
            SERIAL_BAUDRATE,
        )

        print(f"  ✓ OPEN_PROD_BASE_URL: {OPEN_PROD_BASE_URL}")

        if not OPEN_PROD_DB or not OPEN_PROD_API_KEY:
            print("  ⚠ OPEN_PROD_DB / OPEN_PROD_API_KEY: non configurés (créer .env)")
            return False
        print(f"  ✓ OPEN_PROD_DB: {OPEN_PROD_DB}")
        print("  ✓ OPEN_PROD_API_KEY: configurée")
        if OPEN_PROD_MAPPING_FILE.exists():
            print(f"  ✓ Mapping Open Prod: {OPEN_PROD_MAPPING_FILE}")
        else:
            print(f"  ⚠ Mapping Open Prod absent ({OPEN_PROD_MAPPING_FILE}) : copier openprod_mapping.example.json")

        print(f"  ✓ SERIAL_PORT: {SERIAL_PORT}")
        print(f"  ✓ SERIAL_BAUDRATE: {SERIAL_BAUDRATE}")

        return True
    except Exception as e:
        print(f"  ✗ Erreur de configuration: {e}")
        return False

def test_serial_ports():
    """Liste les ports série disponibles."""
    print("\nTesting serial ports...")
    try:
        from core.serial_reader import SerialReader
        ports = SerialReader.list_available_ports()
        if ports:
            print(f"  ✓ {len(ports)} port(s) disponible(s)")
            return True
        else:
            print("  ⚠ Aucun port série détecté (branchez le banc)")
            return True
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return False

def test_data_parser():
    """Lance les tests unitaires (parser sur trames réelles, étiquettes)."""
    print("\nTesting data parser & labels (tests/)...")
    import unittest
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent / 'tests'))
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    status = "✓" if result.wasSuccessful() else "✗"
    print(f"  {status} {result.testsRun} test(s), {len(result.failures)} échec(s), {len(result.errors)} erreur(s)")
    return result.wasSuccessful()

def test_programs():
    """Vérifie le référentiel des programmes (nécessaire aux étiquettes)."""
    print("\nTesting programs catalog...")
    try:
        from config import PROGRAMS_FILE
        from core.labels import ProgramCatalog
        catalog = ProgramCatalog(PROGRAMS_FILE)
        if len(catalog):
            print(f"  ✓ {len(catalog)} programme(s) dans {PROGRAMS_FILE}")
        else:
            print(f"  ⚠ Aucun programme dans {PROGRAMS_FILE} (copier programs.example.json) : pas d'étiquettes")
        return True
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return False

def test_open_prod() -> bool:
    """Distingue un flux réseau fermé (pare-feu) d'une clé ou d'une base refusée."""
    print("\nTesting Open Prod...")
    try:
        import requests
        import urllib3
        from config import OPEN_PROD_BASE_URL, OPEN_PROD_DB, OPEN_PROD_API_KEY, OPEN_PROD_VERIFY_TLS
        from api.client import OpenProdAPIClient
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return False

    if not OPEN_PROD_VERIFY_TLS:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        requests.get(OPEN_PROD_BASE_URL, timeout=10, verify=OPEN_PROD_VERIFY_TLS)
        print(f"  ✓ Serveur joignable en HTTPS: {OPEN_PROD_BASE_URL}")
    except requests.RequestException as e:
        print(f"  ✗ Serveur injoignable: {OPEN_PROD_BASE_URL}")
        print(f"    {type(e).__name__}: {e}")
        print("    → flux HTTPS (443) vers misrv-opp1 fermé depuis ce poste : demande à supportinfo@matferbourgeat.com")
        return False

    if not OPEN_PROD_DB or not OPEN_PROD_API_KEY or OPEN_PROD_API_KEY == 'your_id_secret_here':
        print("  ⚠ Base ou clé API non renseignée dans .env : connexion non testée")
        return True
    client = OpenProdAPIClient()
    try:
        if client.check_connection():
            print(f"  ✓ Connexion acceptée (base {OPEN_PROD_DB})")
            return True
        print(f"  ✗ Connexion refusée (base {OPEN_PROD_DB}): {client.last_error}")
        print("    → vérifier OPEN_PROD_DB et OPEN_PROD_API_KEY dans .env")
        return False
    finally:
        client.close()


def main():
    """Exécute tous les tests."""
    print("=" * 60)
    print("Keck3 Setup Test")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Directories", test_directories()))
    results.append(("Configuration", test_config()))
    results.append(("Serial Ports", test_serial_ports()))
    results.append(("Data Parser", test_data_parser()))
    results.append(("Programs", test_programs()))
    results.append(("Open Prod", test_open_prod()))

    print("\n" + "=" * 60)
    print("Résumé des tests")
    print("=" * 60)

    all_ok = True
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
        if not result:
            all_ok = False

    print()
    if all_ok:
        print("✓ Tous les tests sont passés!")
        print("\nVous pouvez démarrer Keck3 avec:")
        print("  python run.py")
        return 0
    else:
        print("✗ Certains tests ont échoué.")
        print("\nVérifiez les erreurs ci-dessus et réessayez.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
