export interface DatabaseColumn {
  name: string;
  dataType: string;
  nullable: boolean;
  default: string | null;
  primaryKey: boolean;
}

export interface DatabaseIndex {
  name: string | null;
  columnNames: string[];
  unique: boolean;
}

export interface DatabaseNamedColumns {
  name: string | null;
  columnNames: string[];
}

export interface DatabaseCheckConstraint {
  name: string | null;
  expression: string;
}

export interface DatabaseForeignKey {
  name: string | null;
  sourceColumns: string[];
  targetSchema: string;
  targetTable: string;
  targetColumns: string[];
  onUpdate: string | null;
  onDelete: string | null;
}

export interface DatabaseTable {
  schema: string;
  name: string;
  columns: DatabaseColumn[];
  indexes: DatabaseIndex[];
  constraints: {
    primaryKey: DatabaseNamedColumns | null;
    unique: DatabaseNamedColumns[];
    check: DatabaseCheckConstraint[];
  };
  foreignKeys: DatabaseForeignKey[];
}

export interface DatabaseSchema {
  databaseDialect: string;
  defaultSchema: string;
  tables: DatabaseTable[];
}