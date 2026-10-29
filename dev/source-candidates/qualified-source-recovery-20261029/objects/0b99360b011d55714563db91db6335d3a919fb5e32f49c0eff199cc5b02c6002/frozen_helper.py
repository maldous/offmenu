"""Reviewed literal source bindings for the selected private count/ID witness.

No source body discovery, acquisition, registry activation or source JSON factory.
Evidence Assets are supplied by trusted operator code after exact scope review.
"""
from .acceptance import Asset
from .product_input_witness import Table, WitnessContract, WitnessLimits

GIB = 1024**3
USDA_PREFIX = 'FoodData_Central_csv_2026-04-30/'
# Frozen metadata witness9467, not a fresh archive/body observation.
USDA_COLUMNS = {'agricultural_samples': ['fdc_id', 'acquisition_date', 'market_class', 'treatment', 'state'], 'food_protein_conversion_factor': ['food_nutrient_conversion_factor_id', 'value'], 'acquisition_samples': ['fdc_id_of_sample_food', 'fdc_id_of_acquisition_food'], 'sample_food': ['fdc_id'], 'lab_method_nutrient': ['lab_method_id', 'nutrient_id'], 'food_attribute': ['id', 'fdc_id', 'seq_num', 'food_attribute_type_id', 'name', 'value'], 'fndds_ingredient_nutrient_value': ['ingredient code', 'Ingredient description', 'Nutrient code', 'Nutrient value', 'Nutrient value source', 'FDC ID', 'Derivation code', 'SR AddMod year', 'Foundation year acquired', 'Start date', 'End date'], 'sub_sample_result': ['food_nutrient_id', 'adjusted_amount', 'lab_method_id', 'nutrient_name'], 'survey_fndds_food': ['fdc_id', 'food_code', 'wweia_category_code', 'start_date', 'end_date'], 'food_nutrient_conversion_factor': ['id', 'fdc_id'], 'microbe': ['id', 'foodId', 'method', 'microbe_code', 'min_value', 'max_value', 'uom'], 'measure_unit': ['id', 'name'], 'fndds_derivation': ['derivation code', 'derivation description'], 'sub_sample_food': ['fdc_id', 'fdc_id_of_sample_food'], 'input_food': ['id', 'fdc_id', 'fdc_of_input_food', 'seq_num', 'amount', 'sr_code', 'sr_description', 'unit', 'portion_code', 'portion_description', 'gram_weight', 'retention_code'], 'market_acquisition': ['fdc_id', 'brand_description', 'expiration_date', 'label_weight', 'location', 'acquisition_date', 'sales_type', 'sample_lot_nbr', 'sell_by_date', 'store_city', 'store_name', 'store_state', 'upc_code', 'acquisition_number'], 'food_component': ['id', 'fdc_id', 'name', 'pct_weight', 'is_refuse', 'gram_weight', 'data_points', 'min_year_acquired'], 'food': ['fdc_id', 'data_type', 'description', 'food_category_id', 'publication_date'], 'lab_method': ['id', 'description', 'technique'], 'sr_legacy_food': ['fdc_id', 'NDB_number'], 'foundation_food': ['fdc_id', 'NDB_number', 'footnote'], 'food_calorie_conversion_factor': ['food_nutrient_conversion_factor_id', 'protein_value', 'fat_value', 'carbohydrate_value'], 'food_category': ['id', 'code', 'description'], 'food_attribute_type': ['id', 'name', 'description'], 'branded_food': ['fdc_id', 'brand_owner', 'brand_name', 'subbrand_name', 'gtin_upc', 'ingredients', 'not_a_significant_source_of', 'serving_size', 'serving_size_unit', 'household_serving_fulltext', 'branded_food_category', 'data_source', 'package_weight', 'modified_date', 'available_date', 'market_country', 'discontinued_date', 'preparation_state_code', 'trade_channel', 'short_description', 'material_code'], 'wweia_food_category': ['wweia_food_category', 'wweia_food_category_description'], 'food_nutrient_source': ['id', 'code', 'description'], 'food_portion': ['id', 'fdc_id', 'seq_num', 'amount', 'measure_unit_id', 'portion_description', 'modifier', 'gram_weight', 'data_points', 'footnote', 'min_year_acquired'], 'food_nutrient': ['id', 'fdc_id', 'nutrient_id', 'amount', 'data_points', 'derivation_id', 'min', 'max', 'median', 'loq', 'footnote', 'min_year_acquired', 'percent_daily_value'], 'lab_method_code': ['lab_method_id', 'code'], 'food_nutrient_derivation': ['id', 'code', 'description'], 'retention_factor': ['n.gid', 'n.code', 'n.foodGroupId', 'n.description'], 'nutrient': ['id', 'name', 'unit_name', 'nutrient_nbr', 'rank'], 'food_update_log_entry': ['id', 'description', 'last_updated']}
USDA_COMPANION = 'Download API Field Descriptions.xlsx'


def retained_witness_contract(source_id, rights, scope, clock):
    """Explicit source pins; evidence assets confer no permission on their own.

    The retained declared ODbL/DbCL data / CC0 permissions support the selected
    private retain/parse/transform scope. Actual source holds and evidence review
    remain the existing operator's responsibility. No public operation is bound.
    """
    if source_id == 'off':
        original = Asset('off-2026-10-12.jsonl.gz', 13132516914,
            '11f50515dc79181f385df8e59d37ae5ddb85b9b932f84b6411055e026d84680e')
        release, tables, members = '2026-10-12', (), ()
    elif source_id == 'usda-files':
        original = Asset('FoodData_Central_csv_2026-04-30.zip',481517495,
            'c33d91e5c44ddbcd71ed6038714fb648b26089b3f91fabfa3be63d96d5763a01')
        release = '2026-04-30'
        tables = []
        for name, columns in sorted(USDA_COLUMNS.items()):
            key = ('id',) if 'id' in columns else ('fdc_id',) if name in ('food','branded_food') else ()
            references = ()
            if name in ('branded_food','food_nutrient'):
                references = ((('fdc_id',),USDA_PREFIX+'food.csv'),)
            if name == 'food_nutrient':
                references += ((('nutrient_id',),USDA_PREFIX+'nutrient.csv'),)
            tables.append(Table(USDA_PREFIX+name+'.csv',tuple(columns),key,references))
        tables = tuple(tables)
        members = tuple(sorted([t.member for t in tables]+[USDA_PREFIX+USDA_COMPANION]))
    else:
        raise ValueError('witness-source-not-selected')
    return WitnessContract(source_id,release,'full-retained-count-id-witness-v1',original,
        rights,scope,clock,frozenset(('retain','parse','transform')),tables,members)


def retained_witness_limits(source_id, *, protected_bytes_including_floor):
    """Narrow per-pass budget extension; does not alter SharedBudget policy.

    Indexed SQLite btrees perform disk ordering with no external sort files. Caps
    are prospective stop bounds, not measured sufficiency or resource admission.
    The caller reconciles the protected amount freshly; its20GiB floor is included
    once. No existing allocated original or other physical file is charged again.
    """
    if type(protected_bytes_including_floor) is not int or protected_bytes_including_floor < 20*GIB:
        raise ValueError('witness-protected-floor-required')
    common = dict(min_free_bytes=protected_bytes_including_floor,max_id_bytes=64,
                  max_output_bytes=1024**2)
    if source_id == 'off':
        # 8GiB indexed key DB + <2GiB diagnostics/result <=10GiB total.
        return WitnessLimits(max_input_bytes=14*GIB,max_expanded_bytes=192*GIB,
            max_rows=6000000,max_database_bytes=8*GIB,
            max_diagnostic_bytes=2*GIB-1024**2,max_seconds=24*3600,**common)
    if source_id == 'usda-files':
        # 24GiB indexed keys+joins + <4GiB diagnostics/result <=28GiB total.
        return WitnessLimits(max_input_bytes=512*1024**2,max_expanded_bytes=4*GIB,
            max_rows=40000000,max_database_bytes=24*GIB,
            max_diagnostic_bytes=4*GIB-1024**2,max_seconds=12*3600,**common)
    raise ValueError('witness-source-not-selected')
