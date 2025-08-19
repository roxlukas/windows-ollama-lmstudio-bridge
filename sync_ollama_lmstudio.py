import os
import sys
import argparse
import json
import shutil
from pathlib import Path


def create_symlink(src: Path, dst: Path, overwrite: bool = False):
    if dst.exists() or dst.is_symlink():
        if overwrite:
            try:
                dst.unlink()
                print(f"🔄 Nadpisuję: {dst}")
            except Exception as e:
                print(f"❌ Nie mogę usunąć {dst}: {e}")
                return
        else:
            print(f"⏩ Pomijam (już istnieje): {dst}")
            return

    try:
        os.symlink(src, dst, target_is_directory=src.is_dir())
        print(f"✅ Link: {dst} -> {src}")
    except OSError as e:
        print(f"❌ Błąd przy {dst}: {e}")


def build_mapping(manifests_dir: Path, mapping_file: Path):
    mapping = {}
    
    print(f"🔍 Szukam plików w: {manifests_dir}")
    
    # Debug: sprawdź czy katalog istnieje
    if not manifests_dir.exists():
        print(f"❌ Katalog {manifests_dir} nie istnieje!")
        return mapping
    
    all_files = list(manifests_dir.rglob("*"))
    print(f"📁 Znaleziono {len(all_files)} plików/katalogów łącznie")
    
    json_files = [f for f in all_files if f.is_file()]
    print(f"📄 Z tego {len(json_files)} to pliki")

    for mf in json_files:
        print(f"\n🔎 Przetwarzam: {mf}")
        
        try:
            # Sprawdź czy to rzeczywiście plik JSON
            with open(mf, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    print(f"  ⚠️ Pusty plik: {mf}")
                    continue
                    
                # Spróbuj sparsować JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as je:
                    print(f"  ⚠️ Nieprawidłowy JSON w {mf}: {je}")
                    continue

                # Debug: pokaż zawartość
                print(f"  📋 Klucze w JSON: {list(data.keys())}")
                
                # Szukaj digestu w layers (manifest format)
                digest = None
                layers = data.get("layers", [])
                print(f"  📦 Znaleziono {len(layers)} warstw")
                
                if layers:
                    # Typically the largest layer is the model file
                    # Or we can look for specific mediaType
                    largest_layer = None
                    largest_size = 0
                    
                    for layer in layers:
                        layer_digest = layer.get("digest", "")
                        layer_size = layer.get("size", 0)
                        media_type = layer.get("mediaType", "")
                        
                        print(f"    🧩 Warstwa: {layer_digest[:16]}... (rozmiar: {layer_size}, typ: {media_type})")
                        
                        # Szukamy największej warstwy (prawdopodobnie model GGUF)
                        if layer_size > largest_size:
                            largest_size = layer_size
                            largest_layer = layer
                    
                    if largest_layer:
                        digest = largest_layer.get("digest")
                        print(f"  🔑 Wybrano największą warstwę: {digest} (rozmiar: {largest_size})")
                    else:
                        print(f"  ⚠️ Nie znaleziono odpowiedniej warstwy w {mf}")
                        continue
                else:
                    # Fallback - sprawdź czy jest bezpośredni digest
                    digest = data.get("digest")
                    if not digest:
                        print(f"  ⚠️ Brak 'layers' i 'digest' w {mf}")
                        continue
                    print(f"  🔑 Znaleziono bezpośredni digest: {digest}")
                
                if not digest:
                    print(f"  ⚠️ Nie udało się znaleźć digestu w {mf}")
                    continue

                # Analiza ścieżki
                rel = mf.relative_to(manifests_dir)
                print(f"  📂 Relatywna ścieżka: {rel}")
                
                parts = rel.parts
                print(f"  🧩 Części ścieżki: {parts} (długość: {len(parts)})")

                if len(parts) < 3:
                    print(f"  ⚠️ Za krótka ścieżka (mniej niż 3 części)")
                    continue

                domain = parts[0]         # registry.ollama.ai / hf.co / huggingface.co
                vendor = parts[1]         # library / speakleash / someuser
                model = parts[2]          # gpt-oss / polish-llm / some-model
                tag = mf.name             # 20b / q8_0 / q4_k_m
                
                print(f"  🏷️ Domain: {domain}, Vendor: {vendor}, Model: {model}, Tag: {tag}")

                # Generacja nazwy modelu
                if domain == "registry.ollama.ai" and vendor == "library":
                    model_name = f"{model}:{tag}"   # np. gpt-oss:20b
                else:
                    model_name = f"{vendor}/{model}:{tag}"  # np. speakleash/polish-llm:q8_0

                print(f"  📝 Nazwa modelu: {model_name}")
                
                # Store both model name and vendor for later use
                mapping[model_name] = {
                    "digest": digest,
                    "vendor": vendor
                }
                print(f"  ✅ Dodano do mappingu")

        except Exception as e:
            print(f"  ❌ Błąd ogólny przy {mf}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n📊 Końcowy mapping:")
    for model_name, info in mapping.items():
        print(f"  {model_name} → {info['digest']} (vendor: {info['vendor']})")

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Wygenerowano mapping.json ({len(mapping)} modeli)")
    return mapping


def sync_models(mapping: dict, ollama_dir: Path, lmstudio_dir: Path, overwrite: bool):
    print(f"\n🔍 Sprawdzam katalog blobs: {ollama_dir}")
    
    # Debug: pokaż co jest w katalogu blobs
    if ollama_dir.exists():
        blob_files = list(ollama_dir.glob("*"))
        print(f"📦 Znaleziono {len(blob_files)} plików w blobs")
        
        # Pokaż pierwsze kilka plików jako przykład
        sample_files = blob_files[:5]
        for bf in sample_files:
            if bf.is_file():
                size_mb = bf.stat().st_size / (1024*1024)
                print(f"  📄 {bf.name} ({size_mb:.1f} MB)")
        
        if len(blob_files) > 5:
            print(f"  ... i {len(blob_files) - 5} więcej")
    else:
        print(f"❌ Katalog blobs nie istnieje: {ollama_dir}")
        return

    for model_name, info in mapping.items():
        blob_hash = info["digest"]
        vendor = info["vendor"]
        
        # Spróbuj różnych formatów nazw plików
        possible_paths = [
            ollama_dir / blob_hash,  # pełny hash z sha256:
            ollama_dir / blob_hash.replace("sha256:", "sha256-"),  # hash z sha256- (Ollama format)
            ollama_dir / blob_hash.replace("sha256:", ""),  # hash bez prefiksu
            ollama_dir / "sha256" / blob_hash.replace("sha256:", ""),  # hash w podkatalogu sha256
        ]
        
        src_blob = None
        for path in possible_paths:
            if path.exists():
                src_blob = path
                print(f"✅ Znaleziono blob dla {model_name}: {src_blob}")
                break
        
        if not src_blob:
            print(f"❌ Blob dla modelu {model_name} nie istnieje w żadnej z lokalizacji:")
            for path in possible_paths:
                print(f"   ❌ {path}")
            continue

        # Create safe name for directory and filename
        safe_name = model_name.replace(":", "-").replace("/", "_")
        
        # Use vendor name as top directory instead of "models"
        dst_model_dir = lmstudio_dir / vendor / safe_name
        dst_model_dir.mkdir(parents=True, exist_ok=True)

        # Use safe_name as filename instead of "model.gguf"
        dst_file = dst_model_dir / f"{safe_name}.gguf"
        create_symlink(src_blob, dst_file, overwrite=overwrite)
        
        # Utwórz plik metadata dla LM Studio
        create_lmstudio_metadata(dst_model_dir, model_name, src_blob, safe_name)


def create_lmstudio_metadata(model_dir: Path, model_name: str, src_blob: Path, safe_name: str):
    """Tworzy pliki metadata potrzebne przez LM Studio"""
    
    # Parsuj nazwę modelu
    if ":" in model_name:
        base_name, tag = model_name.rsplit(":", 1)
    else:
        base_name, tag = model_name, "latest"
    
    if "/" in base_name:
        org, model = base_name.split("/", 1)
    else:
        org, model = "", base_name
    
    # Pobierz rozmiar pliku
    file_size = src_blob.stat().st_size
    
    # Utwórz config.json (podstawowe metadata modelu)
    config = {
        "name": model_name,
        "display_name": f"{model}:{tag}",
        "organization": org if org else "local",
        "model": model,
        "tag": tag,
        "file_size": file_size,
        "file_path": str(model_dir / f"{safe_name}.gguf"),  # Updated to use safe_name
        "format": "GGUF",
        "source": "ollama"
    }
    
    config_file = model_dir / "config.json"
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"  📄 Utworzono config.json dla {model_name}")
    except Exception as e:
        print(f"  ⚠️ Błąd przy tworzeniu config.json dla {model_name}: {e}")
    
    # Utwórz plik .lmstudio (marker dla LM Studio)
    lmstudio_file = model_dir / ".lmstudio"
    try:
        lmstudio_meta = {
            "model": model_name,
            "imported_from": "ollama",
            "import_date": "2025-01-18",  # można użyć datetime.now().strftime("%Y-%m-%d")
            "blob_hash": src_blob.name
        }
        with open(lmstudio_file, "w", encoding="utf-8") as f:
            json.dump(lmstudio_meta, f, indent=2, ensure_ascii=False)
        print(f"  🏷️ Utworzono .lmstudio dla {model_name}")
    except Exception as e:
        print(f"  ⚠️ Błąd przy tworzeniu .lmstudio dla {model_name}: {e}")


def clean_orphans(mapping: dict, lmstudio_dir: Path):
    expected_by_vendor = {}
    for model_name, info in mapping.items():
        vendor = info["vendor"]
        safe_name = model_name.replace(":", "-").replace("/", "_")
        if vendor not in expected_by_vendor:
            expected_by_vendor[vendor] = set()
        expected_by_vendor[vendor].add(safe_name)

    # Check each vendor directory
    for vendor_dir in lmstudio_dir.iterdir():
        if not vendor_dir.is_dir():
            continue
            
        vendor_name = vendor_dir.name
        expected_models = expected_by_vendor.get(vendor_name, set())
        
        for model_dir in vendor_dir.iterdir():
            if model_dir.is_dir() and model_dir.name not in expected_models:
                try:
                    shutil.rmtree(model_dir)
                    print(f"🗑️ Usunięto osierocony model: {model_dir}")
                except Exception as e:
                    print(f"❌ Nie mogę usunąć {model_dir}: {e}")
        
        # Remove empty vendor directories
        try:
            if not any(vendor_dir.iterdir()):
                vendor_dir.rmdir()
                print(f"🗑️ Usunięto pusty katalog vendor: {vendor_dir}")
        except Exception as e:
            print(f"❌ Nie mogę usunąć pustego katalogu {vendor_dir}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generuje mapping modeli z Ollama i tworzy symlinki do LM Studio"
    )
    parser.add_argument("manifests", type=str, help="Ścieżka do katalogu manifests (np. D:\\AI\\models\\manifests)")
    parser.add_argument("ollama", type=str, help="Ścieżka do katalogu blobs (np. D:\\AI\\models\\blobs)")
    parser.add_argument("lmstudio", type=str, help="Ścieżka do katalogu LM Studio (np. D:\\AI\\LMstudio)")
    parser.add_argument("--mapping", type=str, default="mapping.json", help="Plik mapping.json (domyślnie: mapping.json)")
    parser.add_argument("--overwrite", action="store_true", help="Nadpisuj istniejące symlinki")
    parser.add_argument("--clean", action="store_true", help="Usuń osierocone modele w LM Studio")
    parser.add_argument("--debug", action="store_true", help="Tryb debug - tylko budowanie mappingu")

    args = parser.parse_args()

    manifests_dir = Path(args.manifests)
    ollama_dir = Path(args.ollama)
    lmstudio_dir = Path(args.lmstudio)
    mapping_file = Path(args.mapping)

    mapping = build_mapping(manifests_dir, mapping_file)
    
    if args.debug:
        print("🐛 Tryb debug - zatrzymuję się po budowaniu mappingu")
        return
    
    sync_models(mapping, ollama_dir, lmstudio_dir, overwrite=args.overwrite)

    if args.clean:
        clean_orphans(mapping, lmstudio_dir)


if __name__ == "__main__":
    main()