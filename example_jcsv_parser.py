import pandas as pd
from io import StringIO
import re

def _split_top_commas(s: str) -> list[str]:
    """Split on commas not enclosed in [ ]."""
    parts, buf, depth = [], [], 0
    for ch in s:
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    parts.append(''.join(buf).strip())
    return parts

def _parse_metadata(s: str) -> dict:
    """
    Parse a string like
      'dtypes=[id:int,name:str],created=2025-07-21,refs=[order]'
    into a dict.
    """
    md = {}
    for token in _split_top_commas(s):
        if '=' not in token:
            continue
        key, val = token.split('=', 1)
        key = key.strip()
        val = val.strip()
        # list value
        if val.startswith('[') and val.endswith(']'):
            inner = val[1:-1].strip()
            items = _split_top_commas(inner)
            # strip quotes
            clean = []
            for it in items:
                it = it.strip()
                if (it.startswith('"') and it.endswith('"')) or \
                   (it.startswith("'") and it.endswith("'")):
                    it = it[1:-1]
                clean.append(it)
            md[key] = clean
        else:
            # quoted string?
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            md[key] = val
    # post-process dtypes into dict
    if 'dtypes' in md:
        dt = {}
        for item in md['dtypes']:
            if ':' in item:
                col, typ = item.split(':', 1)
                dt[col.strip()] = typ.strip()
        md['dtypes'] = dt
    return md

def parse_jcsv(path: str) -> dict[str, pd.DataFrame]:
    """
    Parse a .jcsv file into a dict of pandas DataFrames.
    Supports:
      - optional #manifest for random-access
      - per-block metadata in {…}
      - multi-line block refs via metadata key 'refs'
    Returns:
      tables: { block_name -> DataFrame }
    """
    # read all lines
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 1) parse manifest if present
    manifest_map = {}
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx < len(lines) and lines[idx].strip() == '#manifest':
        idx += 1
        # header
        cols = [c.strip() for c in lines[idx].strip().split(',')]
        idx += 1
        # read until blank or next '#'
        while idx < len(lines):
            ln = lines[idx].strip()
            if not ln or ln.startswith('#'):
                break
            vals = [v.strip() for v in ln.split(',')]
            row = dict(zip(cols, vals))
            # record start_line as int
            manifest_map[row['table']] = int(row['start_line'])
            idx += 1

    tables: dict[str, pd.DataFrame] = {}
    metadata: dict[str, dict] = {}

    # 2) parse each block
    i = idx
    header_re = re.compile(r'^#([A-Za-z0-9_]+)(\{.*\})?\s*$')
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        m = header_re.match(line)
        if not m:
            i += 1
            continue
        # block header
        block_name = m.group(1)
        meta_str = m.group(2)
        md = {}
        if meta_str:
            # strip { }
            md = _parse_metadata(meta_str[1:-1])
        metadata[block_name] = md

        # advance to CSV header
        i += 1
        # skip blanks
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break
        col_line = lines[i].rstrip('\n')
        i += 1

        # collect data lines
        data_buf = []
        while i < len(lines):
            ln = lines[i]
            if ln.strip().startswith('#'):
                break
            if ln.strip():
                data_buf.append(ln.rstrip('\n'))
            i += 1

        # read into pandas
        csv_text = '\n'.join([col_line] + data_buf)
        df = pd.read_csv(StringIO(csv_text))

        # apply dtypes if present
        if 'dtypes' in md and isinstance(md['dtypes'], dict):
            dtype_map = {}
            for col, t in md['dtypes'].items():
                if t == 'int':
                    dtype_map[col] = 'Int64'
                elif t == 'float':
                    dtype_map[col] = 'float'
                # str and others keep as object
            if dtype_map:
                df = df.astype(dtype_map)

        tables[block_name] = df

    # 3) resolve multi-line refs
    for tbl, md in metadata.items():
        if 'refs' in md:
            df = tables[tbl]
            for col in md['refs']:
                if col not in df.columns:
                    continue
                # replace each reference with its DataFrame
                df[col] = df[col].apply(lambda ref: tables.get(ref, ref))
            tables[tbl] = df

    return tables


"""
Usage example:

```python
from example_jcsv_parser import parse_jcsv

tables = parse_jcsv('data.jcsv')
users_df   = tables['users']
orders_df  = tables['orders']
```
"""
