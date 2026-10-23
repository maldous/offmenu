-- Recipe connection projection v1. Load after gold.schema.sql, in a transaction.
-- Worker00 alone owns actual execution. Only ready-for-review proposals enter
-- this projection; insertion is not GOLD admission or actual semantic review.
-- Native definitions/instances remain the existing offmenu-recipe-menu-template/1
-- JSON contract validated by the immutable helper; this is no replacement IR.
PRAGMA foreign_keys = ON;

CREATE TABLE gold_recipe_runs (
 run_id TEXT PRIMARY KEY NOT NULL,
 source_occurrence_id TEXT NOT NULL REFERENCES gold_occurrences(occurrence_id),
 recipe_entity_id TEXT NOT NULL REFERENCES gold_entities(entity_id),
 data_class TEXT NOT NULL CHECK(data_class IN ('synthetic','real-qualified')),
 target_language TEXT NOT NULL CHECK(target_language='en'),
 schema_version TEXT NOT NULL CHECK(schema_version='offmenu-gold-recipe-actions/1'),
 native_source_pin TEXT NOT NULL CHECK(native_source_pin='368ef2ce0e42bba3497c5e548f47422a989ea10a'),
 native_modules_json TEXT NOT NULL CHECK(json_valid(native_modules_json) AND json_type(native_modules_json)='object'),
 rules_artifact_sha256 TEXT NOT NULL CHECK(length(rules_artifact_sha256)=64 AND rules_artifact_sha256 NOT GLOB '*[^0-9a-f]*'),
 semantic_review_sha256 TEXT NOT NULL CHECK(length(semantic_review_sha256)=64 AND semantic_review_sha256 NOT GLOB '*[^0-9a-f]*'),
 translation_receipts_sha256 TEXT NOT NULL CHECK(length(translation_receipts_sha256)=64 AND translation_receipts_sha256 NOT GLOB '*[^0-9a-f]*'),
 connection_sha256 TEXT NOT NULL CHECK(length(connection_sha256)=64 AND connection_sha256 NOT GLOB '*[^0-9a-f]*'),
 source_original_sha256 TEXT NOT NULL CHECK(length(source_original_sha256)=64 AND source_original_sha256 NOT GLOB '*[^0-9a-f]*'),
 scale_factor TEXT NOT NULL CHECK(length(trim(scale_factor))>0),
 status TEXT NOT NULL CHECK(status='ready-for-review'),
 gold_admission TEXT NOT NULL CHECK(gold_admission='not-assigned')
);
CREATE TRIGGER gold_recipe_run_qualified BEFORE INSERT ON gold_recipe_runs
WHEN NOT EXISTS (
 SELECT 1 FROM gold_entities e JOIN gold_entity_occurrences eo ON eo.entity_id=e.entity_id
 JOIN gold_occurrences o ON o.occurrence_id=eo.occurrence_id
 WHERE e.entity_id=NEW.recipe_entity_id AND e.domain='recipes' AND e.state='verified'
 AND o.occurrence_id=NEW.source_occurrence_id AND o.domain='recipes' AND o.state='verified')
BEGIN SELECT RAISE(ABORT,'recipe source occurrence and entity must qualify and join'); END;

CREATE TABLE gold_recipe_templates (
 run_id TEXT NOT NULL REFERENCES gold_recipe_runs(run_id),
 template_id TEXT NOT NULL,
 definition_json TEXT NOT NULL CHECK(json_valid(definition_json) AND json_type(definition_json)='object'),
 PRIMARY KEY(run_id,template_id)
);
CREATE TABLE gold_recipe_actions (
 run_id TEXT NOT NULL,
 action_id TEXT NOT NULL,
 template_id TEXT NOT NULL,
 step_id TEXT NOT NULL,
 source_order INTEGER NOT NULL CHECK(source_order>=0),
 sequence_index INTEGER NOT NULL CHECK(sequence_index>=0),
 original_text TEXT NOT NULL CHECK(length(original_text)>0),
 source_language TEXT,
 english_text TEXT NOT NULL CHECK(length(trim(english_text))>0),
 action_concept TEXT NOT NULL,
 phase TEXT NOT NULL CHECK(phase IN ('preparation','cooking','presentation')),
 native_instance_json TEXT NOT NULL CHECK(json_valid(native_instance_json) AND json_type(native_instance_json)='object'),
 unknown_parameters_json TEXT NOT NULL CHECK(json_valid(unknown_parameters_json) AND json_type(unknown_parameters_json)='array'),
 evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json) AND json_type(evidence_json)='array' AND json_array_length(evidence_json)>0),
 PRIMARY KEY(run_id,action_id),
 UNIQUE(run_id,sequence_index),
 UNIQUE(run_id,action_id,sequence_index),
 FOREIGN KEY(run_id,template_id) REFERENCES gold_recipe_templates(run_id,template_id)
);
CREATE TABLE gold_recipe_dependencies (
 run_id TEXT NOT NULL,
 action_id TEXT NOT NULL,
 depends_on TEXT NOT NULL,
 action_sequence INTEGER NOT NULL,
 dependency_sequence INTEGER NOT NULL,
 PRIMARY KEY(run_id,action_id,depends_on),
 CHECK(dependency_sequence<action_sequence),
 FOREIGN KEY(run_id,action_id,action_sequence) REFERENCES gold_recipe_actions(run_id,action_id,sequence_index),
 FOREIGN KEY(run_id,depends_on,dependency_sequence) REFERENCES gold_recipe_actions(run_id,action_id,sequence_index)
);
CREATE TABLE gold_recipe_ingredients (
 run_id TEXT NOT NULL,
 action_id TEXT NOT NULL,
 slot_name TEXT NOT NULL,
 source_ingredient_line_id TEXT NOT NULL,
 ingredient_entity_id TEXT NOT NULL REFERENCES gold_entities(entity_id),
 allocation_json TEXT CHECK(allocation_json IS NULL OR (json_valid(allocation_json) AND json_type(allocation_json)='object')),
 evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json) AND json_type(evidence_json)='array' AND json_array_length(evidence_json)>0),
 PRIMARY KEY(run_id,action_id,slot_name),
 FOREIGN KEY(run_id,action_id) REFERENCES gold_recipe_actions(run_id,action_id)
);
CREATE TRIGGER gold_recipe_ingredient_qualified BEFORE INSERT ON gold_recipe_ingredients
WHEN NOT EXISTS(SELECT 1 FROM gold_entities WHERE entity_id=NEW.ingredient_entity_id AND domain='ingredients' AND state='verified')
BEGIN SELECT RAISE(ABORT,'ingredient requires qualified canonical identity'); END;

CREATE TABLE gold_recipe_materials (
 run_id TEXT NOT NULL,
 material_id TEXT NOT NULL,
 producer_instance_id TEXT NOT NULL,
 producer_sequence INTEGER NOT NULL,
 source_label TEXT NOT NULL CHECK(length(trim(source_label))>0),
 evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json) AND json_type(evidence_json)='array' AND json_array_length(evidence_json)>0),
 PRIMARY KEY(run_id,material_id),
 UNIQUE(run_id,material_id,producer_sequence),
 FOREIGN KEY(run_id,producer_instance_id,producer_sequence) REFERENCES gold_recipe_actions(run_id,action_id,sequence_index)
);
CREATE TABLE gold_recipe_material_inputs (
 run_id TEXT NOT NULL,
 action_id TEXT NOT NULL,
 material_id TEXT NOT NULL,
 action_sequence INTEGER NOT NULL,
 producer_sequence INTEGER NOT NULL,
 evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json) AND json_type(evidence_json)='array' AND json_array_length(evidence_json)>0),
 PRIMARY KEY(run_id,action_id,material_id),
 CHECK(producer_sequence<action_sequence),
 FOREIGN KEY(run_id,action_id,action_sequence) REFERENCES gold_recipe_actions(run_id,action_id,sequence_index),
 FOREIGN KEY(run_id,material_id,producer_sequence) REFERENCES gold_recipe_materials(run_id,material_id,producer_sequence)
);
CREATE TRIGGER gold_recipe_material_dependency BEFORE INSERT ON gold_recipe_material_inputs
WHEN NOT EXISTS (
 WITH RECURSIVE ancestors(action_id) AS (
 SELECT depends_on FROM gold_recipe_dependencies WHERE run_id=NEW.run_id AND action_id=NEW.action_id
 UNION
 SELECT d.depends_on FROM gold_recipe_dependencies d JOIN ancestors a ON d.action_id=a.action_id WHERE d.run_id=NEW.run_id)
 SELECT 1 FROM ancestors a JOIN gold_recipe_materials m ON m.producer_instance_id=a.action_id
 WHERE m.run_id=NEW.run_id AND m.material_id=NEW.material_id)
BEGIN SELECT RAISE(ABORT,'material input requires explicit semantic dependency'); END;

CREATE TABLE gold_recipe_action_support (
 run_id TEXT NOT NULL, action_id TEXT NOT NULL,
 citation_id TEXT NOT NULL REFERENCES gold_citations(citation_id),
 evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json) AND json_type(evidence_json)='array' AND json_array_length(evidence_json)>0),
 PRIMARY KEY(run_id,action_id,citation_id),
 FOREIGN KEY(run_id,action_id) REFERENCES gold_recipe_actions(run_id,action_id)
);
CREATE TABLE gold_recipe_ingredient_support (
 run_id TEXT NOT NULL, action_id TEXT NOT NULL, slot_name TEXT NOT NULL,
 citation_id TEXT NOT NULL REFERENCES gold_citations(citation_id),
 evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json) AND json_type(evidence_json)='array' AND json_array_length(evidence_json)>0),
 PRIMARY KEY(run_id,action_id,slot_name,citation_id),
 FOREIGN KEY(run_id,action_id,slot_name) REFERENCES gold_recipe_ingredients(run_id,action_id,slot_name)
);
CREATE TABLE gold_recipe_material_support (
 run_id TEXT NOT NULL, material_id TEXT NOT NULL,
 citation_id TEXT NOT NULL REFERENCES gold_citations(citation_id),
 evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json) AND json_type(evidence_json)='array' AND json_array_length(evidence_json)>0),
 PRIMARY KEY(run_id,material_id,citation_id),
 FOREIGN KEY(run_id,material_id) REFERENCES gold_recipe_materials(run_id,material_id)
);
CREATE TABLE gold_recipe_material_input_support (
 run_id TEXT NOT NULL, action_id TEXT NOT NULL, material_id TEXT NOT NULL,
 citation_id TEXT NOT NULL REFERENCES gold_citations(citation_id),
 evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json) AND json_type(evidence_json)='array' AND json_array_length(evidence_json)>0),
 PRIMARY KEY(run_id,action_id,material_id,citation_id),
 FOREIGN KEY(run_id,action_id,material_id) REFERENCES gold_recipe_material_inputs(run_id,action_id,material_id)
);

-- Connections are immutable proposals. Changes create a new content-bound run;
-- no UPDATE can bypass insertion qualification/order checks.
CREATE TRIGGER gold_recipe_runs_immutable BEFORE UPDATE ON gold_recipe_runs BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_templates_immutable BEFORE UPDATE ON gold_recipe_templates BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_actions_immutable BEFORE UPDATE ON gold_recipe_actions BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_dependencies_immutable BEFORE UPDATE ON gold_recipe_dependencies BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_ingredients_immutable BEFORE UPDATE ON gold_recipe_ingredients BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_materials_immutable BEFORE UPDATE ON gold_recipe_materials BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_material_inputs_immutable BEFORE UPDATE ON gold_recipe_material_inputs BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_action_support_immutable BEFORE UPDATE ON gold_recipe_action_support BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_ingredient_support_immutable BEFORE UPDATE ON gold_recipe_ingredient_support BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_material_support_immutable BEFORE UPDATE ON gold_recipe_material_support BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
CREATE TRIGGER gold_recipe_material_input_support_immutable BEFORE UPDATE ON gold_recipe_material_input_support BEGIN SELECT RAISE(ABORT,'immutable recipe proposal'); END;
