# JCSV: Joint CSV File Format

JCSV lets you bundle multiple related CSV tables into a single, human-readable file. Each table lives in its own block, and lightweight metadata and an optional manifest make discovery and parsing straightforward.

---

## File Extension

Use `.jcsv` to signal that a file follows the JCSV conventions.

---

## Terminology

- Block  
  A contiguous section of lines: one header and one CSV table.

- Manifest Block  
  An optional top‐level block named `#manifest` that lists every table, its start line, and description.

- Table Block  
  A header line beginning with `#table_name{…}` followed by standard CSV rows.

- Metadata  
  Key/value annotations inside `{…}` on the table header.

---

## Optional Manifest Block

Place this block at the very top to support random access and discovery. Parsers read only this small section to build a lookup of table names to file offsets.

```csv
#manifest
table,start_line,description
users,6,Core user profiles
orders,10,Customer purchase history
products,15,Product catalog
```
If `#manifest` is absent, parsers fall back to scanning for every `#` marker.

### Reserved Manifest Columns

Inside the #manifest block, these column headers are reserved:

- `table` (required): The exact block name of each table.
- `start_line` (optional): The 1-based line number where that block’s header begins.
- `description` (required): A short, human-readable summary of the table’s contents.

---

## Table Blocks

Each table block begins with a header and its metadata, then a standard CSV:

```csv
#table_name{key1=val1,key2=val2,...}
col1,col2,col3
a,1,x
b,2,y
```

Rules for block names:

- Must match `[A-Za-z0-9_]+`
- Must be unique within the file

---

## Metadata Syntax

All metadata sits inside `{…}` on the header line. List values use square brackets `[…]`.

- `key=value`
- Lists: `key=[item1,item2,…]`
- Quoted strings for values containing spaces or commas

### Reserved Metadata Keys:

These **optional** but **reserved** keys may appear inside {…} on any table header. They drive parsing or provide schema information:

- `dtypes`: A list of `column:type` pairs defining each column’s data type. Example: `dtypes=[id:int,name:str,email:str]`.
- `comment`: Free-form text that describes the table. Quoted if it contains spaces or commas. This may serve as a long form of the above `description` column in the `#manifest` section. Example: `comment="User profiles and preferences."`
- `created`: An ISO-formatted date representing when the table was generated. Example: `created=2025-07-21`.
- `version`: A numeric or semantic version tag for the table. Example: `version=1.2.0`.
- `refs`: A list of column names whose values reference other block names for multi-line nesting. Example: `refs=[order,details]`.

Additional keys may be defined arbitrarily as needed if they don't overlap with any reserved keys and keywords.

---

## Multi-Line Block Referencing

JCSV can embed full, multi-row sub-tables per row by defining each nested item as its own block and signalling which column holds those references via metadata. Legacy tools simply see strings, while enhanced parsers pull in the actual block data. If there is no `{refs`, there is no auto-lookup.

### Syntax

1. Define each nested table with a unique block name:

```csv
#order_1
product_name,count
Dell,1

#order_2
product_name,count
Keyboard,10
```

2. In the parent table header, use `{refs=[col1,col2,…]}` to list the reference columns:

```csv
#orders{refs=[order]}
order_id,user_name,order
1,Joe,order_1
2,Alice,order_2
``` 

## Full Example

```csv
#manifest
table,start_line,description
order_1,6,First order details
order_2,10,Second order details
orders,14,Customer orders with embedded details

#order_1
product_name,count
Dell,1
Mouse,2

#order_2
product_name,count
Keyboard,10
Monitor,1

#orders{refs=[order]}
order_id,user_name,order
1,Joe,order_1
2,Alice,order_2
```

---

## Parsing Guidelines

1. Open the file and peek for `#manifest`.  
   - If present, read through to the end of the manifest block and build a map  
     `{ table_name → start_line }`.  
   - If absent, parsers will fall back to scanning for every `#table_name{…}` header.

2. Locate each table block:  
   - With a manifest: seek directly to the `start_line` for a given table.  
   - Without a manifest: read from top to bottom, splitting wherever a line matches `^#([A-Za-z0-9_]+)\{?.*`.

3. For each block header line:  
   - Strip the leading `#`.  
   - Split on the first `{` (if any) to separate the **block name**.  
   - Trim the trailing `}` and parse the **metadata** inside `{…}` by splitting on commas—treating any `[…]` sequences as single list values.

4. Read the CSV rows for that block:  
   - Consume lines after the header until you hit the next `#…` or end-of-file.  
   - Feed those lines into any standard CSV parser.  
   - Store the result in a lookup map `{ block_name → table_data }`.

5. Handle multi-line block references:  
   - If a table’s metadata includes `refs=[col1,col2,…]`, those columns contain **block names** to be expanded.  
   - After loading the parent table, iterate its rows. For each column listed in `refs`, replace the cell value (e.g. `order_1`) with the full data from `table_data["order_1"]`.  
   - If no `refs` key is present, all values remain plain text.

6. Final output:  
   - A collection of top-level tables plus any nested tables injected according to `refs`.  
   - Legacy tools ignore metadata and simply see valid CSV blocks.


---

## Use cases

- Bundling raw data and lookup tables in one file

- Configuration files with multiple parameter grids

- ETL pipelines that ingest related tables together

- Collaborative datasets where editing one file is simpler than managing many

---

Enjoy the simplicity of JCSV—multiple tables, one file, zero fuss.
