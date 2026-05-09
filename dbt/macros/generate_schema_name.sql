-- Override dbt's default schema-naming behaviour.
--
-- By default dbt concatenates the profile schema and the model's +schema:
--   "public" + "staging" → "public_staging"
--
-- This macro makes dbt use the custom schema name directly, so models land in
-- "staging", "intermediate", and "marts" — matching what the analytics SQL
-- and dashboard queries expect.
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
