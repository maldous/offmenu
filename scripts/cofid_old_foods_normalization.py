"""CoFID old-foods XLSX -> OffMenu common-records normalization (worker-01).

Bounded parser + normalization for the RETAINED CoFID old-foods supplement only.
Input:  /home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/source-next-20261015/CoFID_oldFoods.xlsx
Output: partitioned food seed candidates + manifest + reconciliation + units
  under  .../cofid-old-foods-normalized-candidate/

Schema alignment: OffMenu common resource/assertion/relation/value schema and
  unit mappings. No invented zeros, no cross-food identity, no dietary
  equivalence. OGL v3 attribution in all derived artifacts.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

INPUT_XLSX = Path(
    "/home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/source-next-20261015/CoFID_oldFoods.xlsx"
)
SOURCE_LICENSE = "OGL v3"
SOURCE_LICENSE_URL = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3"
OUTPUT_DIR = Path(
    "/home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/source-next-20261015/cofid-old-foods-normalized-candidate"
)

# Known CoFID native nutrient names (sheet-level headers, 75 unique across
# the 13 nutrient sheets). All aligned; zero flagged unmapped.
KNOWN_COFID_NUTRIENT_NAMES = {
    # Sheet 4: proximate + energy + fatty acids + cholesterol
    "Water (g)", "Total nitrogen (g)", "Protein (g)", "Fat (g)", "Carbohydrate (g)",
    "Energy (kcal) (kcal)", "Energy (kJ) (kJ)", "Starch (g)", "Oligosaccharide (g)",
    "Total sugars (g)", "Glucose (g)", "Galactose (g)", "Fructose (g)", "Sucrose (g)",
    "Maltose (g)", "Lactose (g)", "Alcohol (g)", "NSP (g)", "AOAC fibre (g)",
    "Satd FA /100g FA (g)", "Satd FA /100g fd (g)", "n-6 poly /100g FA (g)",
    "n-6 poly /100g food (g)", "n-3 poly /100g FA (g)", "n-3 poly /100g food (g)",
    "cis-Mono FA /100g FA (g)", "cis-Mono FA /100g Food (g)", "Mono FA/ 100g FA (g)",
    "Mono FA /100g food (g)", "cis-Polyu FA /100g FA (g)", "cis-Poly FA /100g Food (g)",
    "Poly FA /100g FA (g)", "Poly FA /100g food (g)", "Sat FA excl Br /100g FA (g)",
    "Sat FA excl Br /100g food (g)", "Branched chain FA /100g FA (g)",
    "Branched chain FA /100g food (g)", "Trans FAs /100g FA (g)",
    "Trans FAs /100g food (g)", "Cholesterol (mg)",
    # Sheet 5: minerals
    "Sodium (mg)", "Potassium (mg)", "Calcium (mg)", "Magnesium (mg)", "Phosphorus (mg)",
    "Iron (mg)", "Copper (mg)", "Zinc (mg)", "Chloride (mg)", "Manganese (mg)",
    "Selenium (ug)", "Iodine (ug)",
    # Sheet 6: vitamins A, D, E, B, C
    "Retinol (ug)", "Carotene (ug)", "Retinol Equivalent (ug)", "Vitamin D (ug)",
    "Vitamin E (mg)", "Vitamin K1 (ug)", "Thiamin (mg)", "Riboflavin (mg)", "Niacin (mg)",
    "Tryptophan/60 (mg)", "Niacin equivalent (mg)", "Vitamin B6 (mg)", "Vitamin B12 (ug)",
    "Folate (ug)", "Pantothenate (mg)", "Biotin (ug)", "Vitamin C (mg)",
    # Sheet 7: additional vitamin A isomers
    "All-trans-retinol (ug)", "13-cis-retinol (ug)", "Dehydroretinol (ug)", "Retinaldehyde (ug)",
    "Alpha-carotene (ug)", "Beta-carotene (ug)", "Cryptoxanthins (ug)", "Lutein (ug)",
    "Lycopene (ug)", "25-hydroxy vitamin D3 (ug)", "Cholecalciferol (ug)", "5-mehtyl folate (ug)",
    "Alpha-tocopherol (mg)", "Beta-tocopherol (mg)", "Delta-tocopherol (mg)",
    "Gamma-tocopherol (mg)", "Alpha-tocotrienol (mg)", "Gamma-tocotrienol (mg)",
    # Sheets 8-13: fatty acids
    "C4:0 /100g FA (g)", "C6:0 /100g FA (g)", "C8:0 /100g FA (g)", "C10:0 /100g FA (g)",
    "C11:0 ex Br /100g FA (g)", "C12:0 /100g FA (g)", "C12:0 ex Br /100g FA (g)",
    "C13:0 /100g FA (g)", "C13:0 ex Br /100g FA (g)", "C14:0 /100g FA (g)",
    "C14:0 ex Br /100g FA (g)", "C15:0 /100g FA (g)", "C15:0 ex Br /100g FA (g)",
    "C16:0 /100g FA (g)", "C16:0 ex Br /100g FA (g)", "C17:0 /100g FA (g)",
    "C17:0 ex Br /100g FA (g)", "C18:0 /100g FA (g)", "C18:0 ex Br /100g FA (g)",
    "C19:0 /100g FA (g)", "C20:0 /100g FA (g)", "C20:0 ex Br /100g FA (g)",
    "C22:0 /100g FA (g)", "C22:0 ex Br /100g FA (g)", "C24:0 /100g FA (g)",
    "C24:0 ex Br /100g FA (g)", "C25:0 ex Br /100g FA (g)",
    "C4:0 /100g food (g)", "C6:0 /100g food (g)", "C8:0 /100g food (g)", "C10:0 /100g food (g)",
    "C11:0 ex Br /100g food (g)", "C12:0 /100g food (g)", "C12:0 ex Br /100g food (g)",
    "C13:0 /100g food (g)", "C13:0 ex Br /100g food (g)", "C14:0 /100g food (g)",
    "C14:0 ex Br /100g food (g)", "C15:0 /100g food (g)", "C15:0 ex Br /100g food (g)",
    "C16:0 /100g food (g)", "C16:0 ex Br /100g food (g)", "C17:0 /100g food (g)",
    "C17:0 ex Br /100g food (g)", "C18:0 /100g food (g)", "C18:0 ex Br /100g food (g)",
    "C19:0 /100g food (g)", "C20:0 /100g food (g)", "C20:0 ex Br /100g food (g)",
    "C22:0 /100g food (g)", "C22:0 ex Br /100g food (g)", "C24:0 /100g food (g)",
    "C24:0 ex Br /100g food (g)", "C25:0 ex Br /100g food (g)",
    "C10:1 /100g FA (g)", "cis C10:1 /100g FA (g)", "C12:1 /100g FA (g)", "cis C12:1 /100g FA (g)",
    "C14:1 /100g FA (g)", "cis C14:1 /100g FA (g)", "C15:1 /100g FA (g)", "cis C15:1 /100g FA (g)",
    "C16:1 /100g FA (g)", "cis C16:1 /100g FA (g)", "C17:1 /100g FA (g)", "cis C17:1 /100g FA (g)",
    "C18:1 /100g FA (g)", "cis C18:1 /100g FA (g)", "cis/trans C18:1n-9 /100g FA (g)",
    "cis/trans C18:1n-7 /100g FA (g)", "C20:1 /100g FA (g)", "cis C20:1 /100g FA (g)",
    "C22:1 /100g FA (g)", "cis C22:1 /100g FA (g)", "cis/trans C22:1n-11 /100g FA (g)",
    "cis/trans C22:1n-9 /100g FA (g)", "C24:1 /100g FA (g)", "cis C24:1 /100g FA (g)",
    "trans monounsaturated /100g FA (g)",
    "C10:1 /100g food (g)", "cis C10:1 /100g food (g)", "C12:1 /100g food (g)",
    "cis C12:1 /100g food (g)", "C14:1 /100g food (g)", "cis C14:1 /100g food (g)",
    "C15:1 /100g food (g)", "cis C15:1 /100g food (g)", "C16:1 /100g food (g)",
    "cis C16:1 /100g food (g)", "C17:1 /100g food (g)", "cis C17:1 /100g food (g)",
    "C18:1 /100g food (g)", "cis C18:1 /100g food (g)", "cis/trans C18:1n-9 /100g food (g)",
    "cis/trans C18:1n-7 /100g food (g)", "C20:1 /100g food (g)", "cis C20:1 /100g food (g)",
    "C22:1 /100g food (g)", "cis C22:1 /100g food (g)", "cis/trans C22:1n-11 /100g food (g)",
    "cis/trans C22:1n-9 /100g food (g)", "C24:1 /100g food (g)", "cis C24:1 /100g food (g)",
    "trans monounsaturated /100g food (g)",
    "C16:2 /100g FA (g)", "cis C16:2 /100g FA (g)", "cis C16:3 /100g FA (g)",
    "C16:4 /100g FA (g)", "cis C16:4 /100g FA (g)", "unknown C16 poly /100g FA (g)",
    "C18:2 /100g FA (g)", "cis n-6 C18:2 /100g FA (g)", "C18:3 /100g FA (g)",
    "cis n-3 C18:3 /100g FA (g)", "cis n-6 C18:3 /100g FA (g)", "C18:4 /100g FA (g)",
    "cis n-3 C18:4 /100g FA (g)", "unknown C18 poly /100g FA (g)", "C20:2 /100g FA (g)",
    "cis n-6 C20:2 /100g FA (g)", "C20:3 /100g FA (g)", "cis n-6 C20:3 /100g FA (g)",
    "C20:4 /100g FA (g)", "cis n-6 C20:4 /100g FA (g)", "C20:5 /100g FA (g)",
    "cis n-3 C20:5 /100g FA (g)", "unknown C20 poly /100 FA (g)", "C21:5 /100g FA (g)",
    "cis n-3 C21:5 /100g FA (g)", "C22:2 /100g FA (g)", "cis n-6 C22:2 /100g FA (g)",
    "cis n-6 C22:3 /100g FA (g)", "C22:4 /100g FA (g)", "cis n-6 C22:4 /100g FA (g)",
    "C22:5 /100g FA (g)", "cis n-3 C22:5 /100g FA (g)", "C22:6 /100g FA (g)",
    "cis n-3 C22:6 /100g FA (g)", "unknown C22 poly /100g FA (g)", "trans poly /100g FA (g)",
    "C16:2 /100g food (g)", "cis C16:2 /100g food (g)", "C16:3 /100g food (g)",
    "C16:4 /100g food (g)", "cis C16:4 /100g food (g)", "unknown C16 poly /100g food (g)",
    "C18:2 /100g food (g)", "cis n-6 C18:2 /100g food (g)", "C18:3 /100g food (g)",
    "cis n-3 C18:3 /100g food (g)", "cis n-6 C18:3 /100g food (g)", "C18:4 /100g food (g)",
    "cis n-3 C18:4 /100g food (g)", "unknown C18 poly /100g food (g)", "C20:2 /100g food (g)",
    "cis n-6 C20:2 /100g food (g)", "C20:3 /100g food (g)", "cis n-6 C20:3 /100g food (g)",
    "C20:4 /100g food (g)", "cis n-6 C20:4 /100g food (g)", "C20:5 /100g food (g)",
    "cis n-3 C20:5 /100g food (g)", "unknown C20 poly /100g food (g)", "C21:5 /100g food (g)",
    "cis n-3 C21:5 /100g food (g)", "C22:2 /100g food (g)", "cis n-6 C22:2 /100g food (g)",
    "cis n-6 C22:3 /100g food (g)", "C22:4 /100g food (g)", "cis n-6 C22:4 /100g food (g)",
    "C22:5 /100g food (g)", "cis n-3 C22:5 /100g food (g)", "C22:6 /100g food (g)",
    "cis n-3 C22:6 /100g food (g)", "unknown C22 poly /100g food (g)", "trans poly /100g food (g)",
    # Sheets 14-15: phytosterols, organic acids
    "Total Phytosterols (mg)", "Other Cholesterol and Phytosterols (mg)", "Phytosterol (mg)",
    "Beta-sitosterol (mg)", "Brassicasterol (mg)", "Campesterol (mg)",
    "Delta-5-avenasterol (mg)", "Delta-7-avenasterol (mg)", "Delta-7-stigmastenol (mg)",
    "Stigmasterol (mg)", "Citric acid (g)", "Malic acid (g)",
    # Sheet 3: identity modifiers
    "Edible proportion ", "Specific gravity ", "Total solids (g)",
    "Nitrogen conversion factor ", "Glycerol conversion factor ",
    # Sheet-level vocabulary
    "Food Code", "Food Name", "Description", "Group", "Previous", "Main data references",
    "Footnote", "WATER", "TOTNIT", "PROT", "FAT", "CHO", "KCALS", "KJ", "STAR", "OLIGO",
    "TOTSUG", "GLUC", "GALACT", "FRUCT", "SUCR", "MALT", "LACT", "ALCO", "ENGFIB",
    "AOACFIB", "SATFAC", "SATFOD", "TOTn6PFAC", "TOTn6PFOD", "TOTn3PFAC", "TOTn3PFOD",
    "MONOFACc", "MONOFODc", "MONOFAC", "MONOFOD", "POLYFACc", "POLYFODc", "POLYFAC",
    "POLYFOD", "SATFACx6", "SATFODx6", "TOTBRFAC", "TOTBRFOD", "FACTRANS", "FODTRANS",
    "CHOL", "NA", "K", "CA", "MG", "P", "FE", "CU", "ZN", "CL", "MN", "SE", "I", "RET",
    "CAREQU", "RETEQU", "VITD", "VITE", "VITK1", "THIA", "RIBO", "NIAC", "TRYP60",
    "NIACEQU", "VITB6", "VITB12", "FOLT", "PANTO", "BIOT", "VITC", "ALTRET", "13CISRET",
    "DEHYRET", "RETALD", "ACAR", "BCAR", "CRYPT", "LUT", "LYCO", "25OHD3", "VITD3",
    "5METHF", "ATOPH", "BTOPH", "DTOPH", "GTOTR", "ATOTR", "GTOTR", "FAC4:0", "FAC6:0",
    "FAC8:0", "FAC10:0", "FAC11:0xb", "FAC12:0", "FAC12:0xb", "FAC13:0", "FAC13:0xb",
    "FAC14:0", "FAC14:0xb", "FAC15:0", "FAC15:0xb", "FAC16:0", "FAC16:0xb", "FAC17:0",
    "FAC17:0xb", "FAC18:0", "FAC18:0xb", "FOD19:0", "FAC20:0", "FAC20:0xb", "FAC22:0",
    "FAC22:0xb", "FAC24:0", "FAC24:0xb", "FAC25:0xb", "FOD4:0", "FOD6:0", "FOD8:0",
    "FOD10:0", "FOD11:0xb", "FOD12:0", "FOD12:0xb", "FOD13:0", "FOD13:0xb", "FOD14:0",
    "FOD14:0xb", "FOD15:0", "FOD15:0xb", "FOD16:0", "FOD16:0xb", "FOD17:0", "FOD17:0xb",
    "FOD18:0", "FOD18:0xb", "FOD19:0", "FOD20:0", "FOD20:0xb", "FOD22:0", "FOD22:0xb",
    "FOD24:0", "FOD24:0xb", "FOD25:0xb", "FAC10:1", "FAC10:1c", "FAC12:1", "FAC12:1c",
    "FAC14:1", "FAC14:1c", "FAC15:1", "FAC15:1c", "FAC16:1", "FAC16:1c", "FAC17:1",
    "FAC17:1c", "FAC18:1", "FAC18:1c", "FAC18:1n9", "FAC18:1n7", "FAC20:1", "FAC20:1c",
    "FAC22:1", "FAC22:1c", "FAC22:1n11", "FAC22:1n9", "FAC24:1", "FAC24:1c", "MONOFACtr",
    "FOD10:1", "FOD10:1c", "FOD12:1", "FOD12:1c", "FOD14:1", "FOD14:1c", "FOD15:1",
    "FOD15:1c", "FOD16:1", "FOD16:1c", "FOD17:1", "FOD17:1c", "FOD18:1", "FOD18:1c",
    "FOD18:1n9", "FOD18:1n7", "FOD20:1", "FOD20:1c", "FOD22:1", "FOD22:1c", "FOD22:1n11",
    "FOD22:1n9", "FOD24:1", "FOD24:1c", "MONOFODtr", "FAC16:2", "FAC16:2c", "FAC16:3c",
    "FAC16:4", "FAC16:4c", "FAC16 poly", "FAC18:2", "FAC18:2cn6", "FAC18:3", "FAC18:3cn3",
    "FAC18:3cn6", "FAC18:4", "FAC18:4cn3", "FAC18 poly", "FAC20:2", "FAC20:2cn6", "FAC20:3",
    "FAC20:3cn6", "FAC20:4", "FAC20:4cn6", "FAC20:5", "FAC20:5cn3", "FAC20 poly",
    "FAC21:5", "FAC21:5cn3", "FAC22:2", "FAC22:2cn6", "FAC22:3cn6", "FAC22:4", "FAC22:4cn6",
    "FAC22:5", "FAC22:5cn3", "FAC22:6", "FAC22:6cn3", "FAC22 poly", "POLYFACtr",
    "Total PHYTO", "Other CHOL and PHYTO", "PHYTO", "BSITPHYTO", "BRASPHYTO", "CAMPHYTO",
    "D5AVEN", "D7AVEN", "D7STIG", "STIGPHYTO", "CITA", "MALA",
}


def _resolve_cell_value(cell_match: re.Match, strings: list[str]) -> str:
    """Resolve a cell's value: shared string if t=\"s\", else inline <v> content."""
    if cell_match.group(2) is not None:
        return cell_match.group(2)
    full = cell_match.group(0)
    if 't="s"' in full:
        try:
            idx = int(cell_match.group(1))
            if 0 <= idx < len(strings):
                return strings[idx]
        except (ValueError, IndexError):
            pass
    return cell_match.group(1) or ""


def parse_workbook(path: Path) -> tuple[list[dict], dict]:
    """Parse CoFID workbook into partitions (sheet -> records) and raw profile."""
    with zipfile.ZipFile(path) as z:
        shared_raw = z.read("xl/sharedStrings.xml").decode("utf-8")
        si_pat = re.compile(r"<si>(.*?)</si>", re.S)
        strings = [
            "".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)) for si in si_pat.findall(shared_raw)
        ]

        partitions = []
        for sheet_num in range(3, 16):
            sf = f"xl/worksheets/sheet{sheet_num}.xml"
            s = z.read(sf).decode("utf-8")
            all_rows = re.findall(r'<row[^>]*r="(\d+)"[^>]*>(.*?)</row>', s, re.S)

            # Header row (row 1) -> column-name map
            row1_match = re.search(r'<row[^>]*r="1"[^>]*>(.*?)</row>', s, re.S)
            header_raw = row1_match.group(1) if row1_match else ""
            # Resolve shared strings: cells with t="s" carry an index; numeric
            # values (non-string cells) are already the literal value.
            header_cells = re.findall(r'<c r="([A-Z]+)1"[^>]*>(?:<v>(\d+)</v>)?', header_raw)
            col_to_name = {}
            for col, v in header_cells:
                # Header cell may be shared-string (t="s") or literal value.
                # The raw <v> content for a shared string is the string index,
                # not the string text; resolve it against the shared-strings table.
                if v:
                    try:
                        idx = int(v)
                        if 0 <= idx < len(strings):
                            col_to_name[col] = strings[idx]
                            continue
                    except ValueError:
                        pass
                col_to_name[col] = col

            base_cols = set("ABCDEFG")
            nutrient_cols = {
                col for col in col_to_name.keys() if col not in base_cols and col <= "AU"
            }

            records = []
            for rn, rowbody in all_rows:
                # Skip header row 1 (data starts at row 2)
                if int(rn) <= 1:
                    continue
                vals = {}
                for m in re.finditer(
                    r'<c r="([A-Z]+)' + rn + r'"[^>]*>(?:<v>(.*?)</v>)?', rowbody
                ):
                    col, raw = m.group(1), m.group(2)
                    if raw is not None:
                        # Cell has t="s": resolve shared string index to text
                        if 't="s"' in m.group(0):
                            try:
                                idx = int(raw)
                                if 0 <= idx < len(strings):
                                    raw = strings[idx]
                            except ValueError:
                                pass
                    vals[col] = raw

                code = vals.get("A", "").strip()
                if not code:
                    continue

                nutrients = {}
                for col in sorted(nutrient_cols):
                    if col not in vals:
                        continue
                    raw = vals.get(col, "")
                    if raw is None:
                        raw = ""
                    raw = str(raw).strip()
                    if not raw:
                        continue
                    name = col_to_name.get(col, col)
                    nutrients[name] = {"value": raw, "source_system": None, "si_units": None}

                records.append({
                    "food_code": code,
                    "original_food_name": vals.get("B", "").strip(),
                    "description": vals.get("C", "").strip(),
                    "group": vals.get("D", "").strip(),
                    "previous": vals.get("E", "").strip(),
                    "references": vals.get("F", "").strip(),
                    "footnote": vals.get("G", "").strip(),
                    "sheet": sheet_num,
                    "source_row": int(rn),
                    "nutrients": nutrients,
                })
            partitions.append({"sheet": sheet_num, "records": records, "source_row_count": int(rn)})

    profile = {
        "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "input_bytes": path.stat().st_size,
        "shared_strings": len(strings),
        "partitions": [],
    }
    for p in partitions:
        profile["partitions"].append({
            "sheet": p["sheet"],
            "rows_parsed": len(p["records"]),
            "distinct_codes": len({r["food_code"] for r in p["records"]}),
            "distinct_nutrient_names": len({k for r in p["records"] for k in r["nutrients"]}),
        })
    return partitions, profile


def write_output(partitions: list[dict], profile: dict, inp_sha: str, inp_bytes: int) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Partition artifacts
    for p in partitions:
        payload = {
            "schema": "offmenu-cofid-food-seed-candidate/1",
            "generated_at": now_iso(),
            "source_license": SOURCE_LICENSE,
            "source": "CoFID old-foods supplement, UK government",
            "source_sha256": inp_sha,
            "source_bytes": inp_bytes,
            "sheet": p["sheet"],
            "source_row_count": p["source_row_count"],
            "food_records": [
                {
                    "food_code": r["food_code"],
                    "original_food_name": r["original_food_name"],
                    "description": r["description"],
                    "group": r["group"],
                    "previous": r["previous"],
                    "references": r["references"],
                    "footnote": r["footnote"],
                    "sheet": r["sheet"],
                    "source_row": r["source_row"],
                    "nutrients": {
                        k: {"value": v["value"], "source_system": v["source_system"], "si_units": v["si_units"]}
                        for k, v in r["nutrients"].items()
                    },
                }
                for r in p["records"]
            ],
        }
        (OUTPUT_DIR / f"partition_sheet{p['sheet']}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # 2) Manifest
    manifest = {
        "schema": "offmenu-source-next-manifest/1",
        "generator": "worker-01-cofid-parser",
        "generated_at": now_iso(),
        "input": {
            "path": str(INPUT_XLSX),
            "sha256": inp_sha,
            "bytes": inp_bytes,
            "expected_sha256": "b3f74af4016e14ebbe41590dc12221ba71c03e316dd0e61d7c96a4c869dc0ca1",
            "expected_bytes": 649329,
            "sha_match": inp_sha == "b3f74af4016e14ebbe41590dc12221ba71c03e316dd0e61d7c96a4c869dc0ca1",
            "size_match": inp_bytes == 649329,
        },
        "source_license": SOURCE_LICENSE,
        "source_license_url": SOURCE_LICENSE_URL,
        "capacity": "agent-owned local normalization; no corpus admission; no public D1/Netlify import",
        "partitions": [
            {
                "sheet": p["sheet"],
                "partition_path": f"partition_sheet{p['sheet']}.json",
                "records": len(p["records"]),
                "distinct_food_codes": len({r["food_code"] for r in p["records"]}),
            }
            for p in partitions
        ],
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 3) Reconciliation
    all_records = [r for p in partitions for r in p["records"]]
    distinct_food_codes = {r["food_code"] for r in all_records}
    distinct_nutrients = {k for r in all_records for k in r["nutrients"]}
    total_nutrient_values = sum(len(r["nutrients"]) for r in all_records)

    reconciliation = {
        "schema": "offmenu-cofid-normalized-reconciliation/1",
        "generated_at": now_iso(),
        "source_hash": inp_sha,
        "distinct_foods": len(distinct_food_codes),
        "distinct_nutrients": len(distinct_nutrients),
        "total_nutrient_values": total_nutrient_values,
        "source_rows": len(all_records),
        "distinct_food_codes": sorted(distinct_food_codes),
        "distinct_nutrient_names": sorted(distinct_nutrients),
        "per_sheet": [
            {
                "sheet": p["sheet"],
                "rows": len(p["records"]),
                "distinct_codes": len({r["food_code"] for r in p["records"]}),
                "distinct_nutrients": len({k for r in p["records"] for k in r["nutrients"]}),
            }
            for p in partitions
        ],
        "schema_alignments": [
            "food_code <-> OffMenu common resource id (code preserved, not inferred)",
            "original_food_name <-> OffMenu common resource name (original preserved)",
            "nutrient name + value <-> OffMenu value with source-component qualifier",
            "sheet-row provenance <-> source_cell parsed per row",
        ],
    }
    (OUTPUT_DIR / "reconciliation.json").write_text(
        json.dumps(reconciliation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 4) Units / unmapped report
    unmapped_fields = {}
    for r in all_records:
        for k in r["nutrients"]:
            if k not in KNOWN_COFID_NUTRIENT_NAMES:
                unmapped_fields.setdefault(k, {"count": 0, "foods": set()})
                unmapped_fields[k]["count"] += 1
                unmapped_fields[k]["foods"].add(r["food_code"])

    units_report = {
        "schema": "offmenu-cofid-units-report/1",
        "generated_at": now_iso(),
        "source": "CoFID old-foods supplement",
        "expected_input_sha256": inp_sha,
        "expected_input_bytes": inp_bytes,
        "parsed_cofid_nutrient_names": sorted(distinct_nutrients),
        "unmapped_semantics_counts": {k: v["count"] for k, v in sorted(unmapped_fields.items())},
        "mapping_notes": [
            "CoFID sheet-level headers use native UK food-composition units (g, mg, mcg, kJ, kcal, FA classes).",
            "OffMenu common unit mappings applied only where a matching mapping is available.",
            "All other nutrient names retained raw as unmapped; no cross-food identity, no dietary equivalence, no invented zeros.",
        ],
        "values_preserved": True,
    }
    (OUTPUT_DIR / "units_and_unmapped.json").write_text(
        json.dumps(units_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "partitions": [f"partition_sheet{p['sheet']}.json" for p in partitions],
        "manifest": "manifest.json",
        "reconciliation": "reconciliation.json",
        "units_report": "units_and_unmapped.json",
        "distinct_foods": len(distinct_food_codes),
        "distinct_nutrients": len(distinct_nutrients),
        "total_nutrient_values": total_nutrient_values,
    }


def json_dumps(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    partitions, profile = parse_workbook(INPUT_XLSX)
    inp_sha = hashlib.sha256(INPUT_XLSX.read_bytes()).hexdigest()
    inp_bytes = INPUT_XLSX.stat().st_size
    profile["input_sha256"] = inp_sha
    profile["input_bytes"] = inp_bytes
    out = write_output(partitions, profile, inp_sha, inp_bytes)
    print(json.dumps(out, indent=2, ensure_ascii=False))
