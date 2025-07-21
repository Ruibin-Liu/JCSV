import streamlit as st
import pandas as pd
import re
from io import StringIO
import ast

st.set_page_config(page_title="🔬 JCSV Editor", layout="wide")
st.title("🔬 JCSV Web Editor")

# ------------------------
# 📦 Upload JCSV File
# ------------------------
uploaded_file = st.file_uploader("Upload a .jcsv file", type="jcsv")

# ------------------------
# 🧠 Parser for JCSV
# ------------------------
def parse_jcsv(raw_text):
    blocks, metadata = {}, {}
    current_block, block_lines = None, []

    for line in raw_text.splitlines():
        if line.startswith("#"):
            if current_block and block_lines:
                blocks[current_block] = block_lines
                block_lines = []
            match = re.match(r"#(\w+)(\{.*\})?", line)
            if match:
                current_block = match.group(1)
                metadata[current_block] = match.group(2) or ""
        elif current_block:
            block_lines.append(line)

    if current_block and block_lines:
        blocks[current_block] = block_lines

    return blocks, metadata

# ------------------------
# 🧮 Metadata Form Editor
# ------------------------
def edit_metadata(meta):
    cleaned = meta.strip("{}") if meta else ""
    pairs = re.findall(r"(\w+)=\[.*?\]|(\w+)=[^,]+", cleaned)
    meta_dict = {}

    for raw in pairs:
        item = next(filter(None, raw))
        if "=" in item:
            key, val = item.split("=", 1)
            key, val = key.strip(), val.strip()
            meta_dict[key] = val

    st.markdown("🧠 **Edit Metadata Fields**")
    new_meta = {}
    for k, v in meta_dict.items():
        new_meta[k] = st.text_input(f"{k}", v)

    meta_str = ",".join([f"{k}={v}" for k, v in new_meta.items()])
    return "{" + meta_str + "}"

# ------------------------
# 🔎 Ref Expansion
# ------------------------
def expand_refs(df, refs, table_data):
    for col in refs:
        if col in df.columns:
            df[col] = df[col].apply(lambda val: table_data[val] if val in table_data else val)
    return df

# ------------------------
# 🚀 Main Logic
# ------------------------
if uploaded_file:
    raw = uploaded_file.read().decode("utf-8")
    blocks, metadata = parse_jcsv(raw)
    edited_blocks = {}

    st.sidebar.header("📜 Manifest")
    for name in blocks:
        st.sidebar.markdown(f"- `{name}`")

    all_tables = {}
    for name, lines in blocks.items():
        st.subheader(f"📦 Block: `{name}`")
        meta = metadata.get(name, "")
        new_meta = edit_metadata(meta)

        try:
            df = pd.read_csv(StringIO("\n".join(lines)))
        except:
            st.warning("⚠️ Unable to parse CSV content in this block.")
            continue

        refs = re.search(r"refs=\[([^\]]+)\]", new_meta)
        if refs:
            ref_cols = [x.strip() for x in refs.group(1).split(",")]
            df = expand_refs(df, ref_cols, all_tables)

        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{name}"
        )

        edited_blocks[name] = {
            "data": edited_df,
            "metadata": new_meta
        }

        all_tables[name] = edited_df

    # ------------------------
    # ➕ Create New Block
    # ------------------------
    with st.expander("➕ Create New Block"):
        new_name = st.text_input("New block name")
        new_meta = st.text_input("Metadata `{...}`", value="{comment=\"New block.\"}")
        new_csv = st.text_area("CSV content", value="col1,col2\nval1,val2")
        if st.button("Create Block"):
            try:
                df_new = pd.read_csv(StringIO(new_csv))
                edited_blocks[new_name] = {
                    "data": df_new,
                    "metadata": new_meta
                }
                st.success(f"✅ Block `{new_name}` created.")
            except:
                st.error("❌ CSV parsing failed.")

    # ------------------------
    # 🗑️ Delete Block
    # ------------------------
    with st.expander("🗑️ Delete Block"):
        block_to_delete = st.selectbox("Select block to delete", list(edited_blocks.keys()))
        if st.button("Delete Block"):
            edited_blocks.pop(block_to_delete, None)
            st.success(f"🗑️ Block `{block_to_delete}` removed.")

    # ------------------------
    # 📉 Preview Ref Graph
    # ------------------------
    with st.expander("🔗 Preview Block References"):
        st.markdown("This shows which blocks refer to others via `refs`.")
        graph_data = []
        for name, meta in metadata.items():
            refs = re.search(r"refs=\[([^\]]+)\]", meta or "")
            if refs:
                df = edited_blocks[name]["data"]
                for col in refs.group(1).split(","):
                    if col.strip() in df.columns:
                        for ref_name in df[col.strip()].unique():
                            graph_data.append((name, ref_name))

        if graph_data:
            st.write("Block Relationships:")
            rel_df = pd.DataFrame(graph_data, columns=["Parent Block", "Referenced Block"])
            st.dataframe(rel_df)
        else:
            st.info("No refs relationships found.")

    # ------------------------
    # ⬇️ Export JCSV
    # ------------------------
    st.divider()
    if st.button("📤 Export as JCSV"):
        output = []

        # Add manifest first (optional)
        if "manifest" in edited_blocks:
            output.append("#manifest")
            manifest_df = edited_blocks["manifest"]["data"]
            output.append(manifest_df.to_csv(index=False).strip())

        for name, content in edited_blocks.items():
            if name == "manifest":
                continue
            meta = content["metadata"]
            df = content["data"]
            header = f"#{name}{meta}" if meta else f"#{name}"
            output.append(header)
            output.append(df.to_csv(index=False).strip())

        final_jcsv = "\n".join(output)
        st.download_button(
            label="⬇️ Download Edited JCSV",
            data=final_jcsv,
            file_name="edited_file.jcsv",
            mime="text/plain"
        )
