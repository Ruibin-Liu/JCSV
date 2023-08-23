# JCSV: Joint CSV File Format
When we have multiple CSV files which contain different columns but they are related to each other, it is better to put them together into a same readable and editable file as a normal CSV file. 

## Ideas

- Separate different CSV files with special lines that are normally ignored by most CSV parsers.
- A JCSV file is parsed as a dict of individual CSV blocks.
- Use '#' to separate differenct CSV blocks

## Terminology

- `CSV content`: block of lines of a common CSV file
- `JCSV`: the proposed JCSV (Joint CSV) file format (recommended file extension: .jcsv)
- `CSV title`: A string acts as the title of the containing CSV content
- `CSV title line`: `#` + `CSV title`
- `CSV block`: a `CSV title` followed by one `CSV content`

## Example
With two typical `CSV` files `csv1.csv` and `csv2.csv` with corresponding contents:
```csv
foo,bar
1,1.9
2,777
```
and 
```
goo,car,caz
John,0,'r'
Hank,1,'b'
```
A JCSV file combining them is defined as:
```jcsv
#csv1
foo,bar
1,1.9
2,777
#csv2
goo,car,caz
John,0,'r'
Hank,1,'b'
```
We used the `#` symbol and the base name of the CSV file as the `CSV title` and the lines between it and the next `CSV title` or EOF are the `CSV content` belonging to that CSV file.

In a JCSV file, the string in the `CSV title` can be any string but it is recommened to be a legal file name, and even better to be a legal variable name in most programming languages. 

It is easier to separate a JCSV file into composing CSV files using the `CSV title`s as file names; it is easier to parse a JCSV file into a dict (python `Dict`) of Pandas Dataframes using the `CSV title`s as keys.
