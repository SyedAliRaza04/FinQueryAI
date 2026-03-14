import json
from sqlalchemy import create_engine, inspect
from typing import Dict, Any, List, Optional

class SchemaRepository:
    """
    A component to extract relational schema, metadata, and relationships from a SQL database.
    """

    def __init__(self, db_connection_string: str):
        self.engine = create_engine(db_connection_string)
        self.inspector = inspect(self.engine)

    def get_table_names(self) -> List[str]:
        """Returns a list of all table names in the database."""
        return self.inspector.get_table_names()

    def get_columns_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Extracts detailed information about columns for a given table.
        Includes name, type, nullable, default, and inferred descriptions.
        """
        columns = self.inspector.get_columns(table_name)
        enriched_columns = []
        
        for col in columns:
            col_info = {
                "name": col['name'],
                "type": str(col['type']),
                "nullable": col['nullable'],
                "default": str(col['default']) if col['default'] else None,
                "primary_key": False, # Will be updated later
                "foreign_key": None,  # Will be updated later
                "description": self._infer_column_description(col['name'], str(col['type']))
            }
            enriched_columns.append(col_info)
            
        return enriched_columns

    def get_pk_info(self, table_name: str) -> List[str]:
        """Returns the primary key column names."""
        pk_constraint = self.inspector.get_pk_constraint(table_name)
        return pk_constraint.get('constrained_columns', [])

    def get_fk_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Returns foreign key constraints."""
        return self.inspector.get_foreign_keys(table_name)

    def _infer_column_description(self, col_name: str, col_type: str) -> str:
        """
        Generates an intelligent description based on column name and type.
        This is a heuristic-based approach.
        """
        col_name_lower = col_name.lower()
        
        if "id" in col_name_lower:
            if col_name_lower == "id" or col_name_lower == "uuid":
                return "Unique identifier for the record."
            return f"Identifier referencing {col_name_lower.replace('_id', '').replace('id', '')} entity."
        
        if "name" in col_name_lower:
            return f"Name of the {col_name_lower.replace('_name', '').replace('name', '')}."
        
        if "email" in col_name_lower:
            return "Email address for contact."
        
        if "phone" in col_name_lower:
            return "Phone number for contact."
        
        if "date" in col_name_lower or "time" in col_name_lower or "created_at" in col_name_lower:
            return "Timestamp or date of the event/record."
            
        if "balance" in col_name_lower:
            return "Financial balance amount."
            
        if "age" in col_name_lower:
            return "Age of the customer/entity."
            
        if "job" in col_name_lower:
            return "Occupation or job title."
            
        if "education" in col_name_lower:
            return "Educational qualification level."

        return f"Represents the {col_name.replace('_', ' ')}."

    def extract_full_schema(self) -> Dict[str, Any]:
        """
        Extracts the complete schema of the database including tables, columns, 
        relationships, and metadata.
        """
        schema_info = {
            "database_type": str(self.engine.dialect.name),
            "tables": {}
        }

        table_names = self.get_table_names()

        for table in table_names:
            columns = self.get_columns_info(table)
            pk = self.get_pk_info(table)
            fks = self.get_fk_info(table)
            
            # Map PK/FK to columns
            for col in columns:
                if col['name'] in pk:
                    col['primary_key'] = True
                
                for fk in fks:
                    if col['name'] in fk['constrained_columns']:
                        col['foreign_key'] = {
                            "referred_table": fk['referred_table'],
                            "referred_columns": fk['referred_columns']
                        }

            schema_info['tables'][table] = columns
            
        return schema_info

    def extract_ddl_schema(self) -> str:
        """
        Extracts the schema as concise CREATE TABLE DDls.
        This provides a dense, token-efficient prompt for the LLM.
        """
        schema_json = self.extract_full_schema()
        ddl_statements = []

        for table_name, columns in schema_json.get('tables', {}).items():
            col_defs = []
            pk_defs = []
            fk_defs = []

            for col in columns:
                col_def = f"  {col['name']} {col['type']}"
                if not col['nullable']:
                    col_def += " NOT NULL"
                if col['primary_key']:
                    pk_defs.append(col['name'])
                
                # Add commented description if useful
                col_def += f" -- {col['description']}"
                col_defs.append(col_def)

            table_def = f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs)
            if pk_defs:
                table_def += f",\n  PRIMARY KEY ({', '.join(pk_defs)})"
            table_def += "\n);"
            ddl_statements.append(table_def)

        return "\n\n".join(ddl_statements)
