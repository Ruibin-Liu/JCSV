import pandas as pd

def export_jcsv(
    tables: dict[str, pd.DataFrame],
    path: str,
    descriptions: dict[str, str] | None = None,
) -> None:
    """
    Write a JCSV file with a correct #manifest block.
    
    tables:        dict of table_name -> DataFrame
    path:          where to write the .jcsv file
    descriptions:  optional dict of table_name -> human description
    """
    descriptions = descriptions or {}
    
    # 1) Precompute how many lines the manifest will take
    #    (#manifest + header + one line per table + 1 empty line)
    manifest_line_count = 1 + 1 + len(tables) + 1
    
    # 2) Compute start_line for each table
    start_lines: dict[str, int] = {}
    cursor = manifest_line_count + 1
    for name, df in tables.items():
        start_lines[name] = cursor
        # each block: 1 title + 1 column header + N data rows + 1 empty line
        cursor += 2 + len(df) + 1
    
    # 3) Write everything
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        # 3a) manifest block
        f.write("#manifest\n")
        f.write("table,start_line,description\n")
        for name in tables:
            desc = descriptions.get(name, "")
            # escape any commas in description
            if "," in desc:
                desc = f'"{desc}"'
            f.write(f"{name},{start_lines[name]},{desc}\n")
        
        # 3b) each table block
        for name, df in tables.items():
            # metadata: compute dtypes
            dt_specs = []
            for col, dtype in df.dtypes.items():
                dt = str(dtype)
                if "int" in dt:
                    t = "int"
                elif "float" in dt:
                    t = "float"
                else:
                    t = "str"
                dt_specs.append(f"{col}:{t}")
            meta = f"dtypes=[{','.join(dt_specs)}]"
            
            # optional comment metadata
            comment = descriptions.get(name)
            if comment:
                # quote if needed
                val = comment if '"' not in comment else comment.replace('"', '\\"')
                meta += f",comment=\"{val}\""
            
            # header title
            f.write(f"\n#{name}{{{meta}}}\n")
            
            # write the CSV portion
            df.to_csv(f, index=False)

"""
Example usage:

```python
# prepare some DataFrames
users = pd.DataFrame({
    "id": [1, 2],
    "name": ["Alice", "Bob"],
    "email": ["a@x.com", "b@x.com"],
})
orders = pd.DataFrame({
    "order_id": [100, 200],
    "user_id": [1, 2],
    "total": [9.99, 14.50],
})

export_jcsv(
    tables={"users": users, "orders": orders},
    path="data.jcsv",
    descriptions={"users": "Core user profiles", "orders": "Purchase history"},
)
```
"""
