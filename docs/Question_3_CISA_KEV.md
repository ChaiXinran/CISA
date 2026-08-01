# Question 3: Given the time when vulnerabilities were exploited, information about the manufacturers, and analysis of the vulnerability structures

## I. Problem Description

There are numerous vulnerabilities in both software and hardware. It’s difficult to determine which vulnerabilities have actually been exploited in real-world attacks, based solely on vulnerability IDs or descriptions. The U.S. Cybersecurity and Infrastructure Security Agency (CISA) maintains the Known Exploited Vulnerabilities Catalog (KEV), which includes vulnerabilities that have a CVE ID, for which there are clear remediation instructions, and for which there is reliable evidence of actual exploitation in the wild. CISA uses this catalog as an important factor in determining the priority of vulnerability mitigation efforts. However, this catalog doesn’t cover all vulnerabilities, nor does it provide information about how often a vulnerability has been exploited, how many devices are affected, or a unified severity score for each vulnerability.

This question uses the course attachment `CISA_KEV_2026-07-29.json`. It contains a total of 1,656 vulnerability records.

The top level of JSON contains:

```text
title, catalogVersion, dateReleased, count, vulnerabilities
```

Each record in the `vulnerabilities` array contains the following 11 fields:

```text
cveID, vendorProject, product, vulnerabilityName,
dateAdded, shortDescription, requiredAction, dueDate,
knownRansomwareCampaignUse, notes, cwes
```

Among them, `cwes` is a list. One CVE can correspond to multiple CWE codes, or the list can be empty. `dateAdded` represents the date when the vulnerability was added to the KEV directory. It’s not the date the vulnerability was disclosed, the date an attack occurred, or the date the CVE number was assigned. `dueDate` refers to the deadline for taking required actions as specified in the CISA catalog. This isn’t a universal deadline that all organizations must comply with, nor is it the actual date when repairs were completed. `knownRansomwareCampaignUse` can only take the values “Known” or “Unknown”. “Unknown” indicates that CISA has not confirmed that this vulnerability has been exploited by ransomware. This should not be interpreted as “not used in ransomware activities”.

This task requires using Python to parse nested JSON data. The required tasks include verifying the data structure, analyzing the time and expiration dates of entries, compiling statistics on manufacturers and their product combinations, analyzing the concentration of manufacturer-related tags, gathering statistics on CWE-related tags, and creating reusable filtering functions. All conclusions must be based solely on the data contained in the local KEV snapshot. It is not allowed to use the number of records to assess a manufacturer’s product quality or the actual probability of being attacked.

## II. Experimental Requirements

1. **[20 points]** Read the top-level metadata and vulnerability array from the JSON file. Verify the fields, CVE uniqueness, dates, enum values, and CWE lists. Then export the processed data.
2. **[20 points]** Analyze the monthly and annual distributions of `dateAdded`, the maturity structure of `dueDate-dateAdded`, and the confirmation status of ransomware in the Known and Unknown categories.
3. **【20 Points】** Calculate the number of records and their proportion for each manufacturer and manufacturer-product combination. Determine the concentration of manufacturer labels, and generate either a static image or an interactive HTML report.
4. **[20 points]** Correctly expand multi-value CWEs, compare the main CWEs, and implement query functions that can combine dates, manufacturers, ransomware status, and CWE conditions.
5. **[14 points] Optional:** Design a GUI for KEV directory retrieval and visualization.
6. **[6 points] Optional:** Use other machine learning methods to perform data analysis.

In all CSV files for this question, the percentage fields named `share`, `cumulative_share`, `known_share`, and `unknown_share` should be stored as decimals in \([0,1]\). These values should be formatted as percentages in the reports and charts. The HHI for manufacturers must also be calculated using these percentage values in \([0,1]\). Do not square the percentage values directly.

## III. Instructions for Required Parts

### 1. JSON reading, structure processing, and data validation (20 points)

#### (1) Read top-level metadata and the vulnerability array

First, use the Python standard library’s `json` module to read the file. Then, use `pd.json_normalize` or an equivalent method to convert the `vulnerabilities` array into a DataFrame. The program outputs and verifies the result:

- `catalogVersion`；
- `dateReleased`；
- Top-level `count`;
- The actual length of the `vulnerabilities`;
- The set of original fields for each vulnerability record.

The top-level `count` must match the number of rows in the DataFrame. `cwes` should remain a list; it cannot be treated as a regular string during the reading process.

#### (2) Complete field and logical validation

Check:

1. Whether it contains 1,656 records and 11 original vulnerability fields.
2. Is the `cveID` not empty, unique, and meets the regular expression `^CVE-[0-9]{4}-[0-9]{4,19}$`?
3. Can both `dateAdded` and `dueDate` be parsed in the `YYYY-MM-DD` format?
4. Are all the conditions `dueDate >= dateAdded` met?
5. `knownRansomwareCampaignUse` 是否只包含 `Known` 和 `Unknown`；
6. Are all elements in `cwes` lists? And does each non-empty element satisfy the pattern `^CWE-[0-9]+$`?
7. Check whether there are any null values or empty strings for the manufacturer, product, vulnerability name, description, and required action.
8. The number of non-null values, the number of null values, and the data type for each field.

The CWES field contains 171 empty records in the attachment. All other main fields are complete. An empty CWE field indicates that no corresponding CWE codes are provided in the attachment. Do not fill in values like `CWE-0`, “Unknown”, or common CWE codes. These records should be retained for tasks that do not involve CWE codes.

In addition, 6 records in `vendorProject` and 10 records in `product` contain leading or trailing spaces. The original fields must be retained. Additionally, `vendor_clean` and `product_clean` should be created, using `.str.strip()` to remove only leading and trailing spaces. For grouping, sorting, and querying, only the cleaned fields should be used. Fuzzy matching, spelling corrections, or subjective merging of names are not allowed.

### 2. Date of addition to the catalog, disposal deadline, and confirmation status of ransomware (20 minutes)

#### (1) Analyze the time when items were added to the directory

Create a sequence of monthly record counts from November 2021 to July 2026, sorted by `dateAdded`. Also, calculate the record counts for each year. The annual tables must indicate the first and last months covered by the data for that year, as well as the total number of months covered. Years 2021 and 2026 should be marked as incomplete years.

When comparing different years, at least one of the following comparable methods should be used:

- Only years that are completely covered in the attachments are compared.
- Compare the same periods from January to July across different years.
- All months are displayed directly, with clear indications that 2021 starts in November and 2026 ends on July 29th.

During the initial phase of directory establishment, existing vulnerabilities may be added to it. Therefore, the monthly and annual numbers of additions should be interpreted as part of the routine maintenance and updates of the KEV directory. They cannot be considered as the number of vulnerabilities disclosed, the number of attacks, or indicators of network attack trends.

#### (2) Calculating the term structure

Define the number of days for each record’s directory disposal period:

$$
D_i = dueDate_i - dateAdded_i
$$

`Deadline_days` represents the number of calendar days between two dates, without counting the starting date as one day. The minimum, quartiles, median, mean, and maximum values for these durations are calculated to create a frequency table of all possible duration periods. The distribution of these durations is then analyzed based on the `added_year` parameter. This value represents the action window specified in the guidelines, not the actual time required for a particular organization to fix the issue. Nor should the severity of a vulnerability be determined solely based on its duration.

#### (3) Analyze the status of ransomware detection

Count the number and percentage of Known and Unknown entries separately, and create a cross-table based on `added_year`. The percentage of Known entries for a given year is defined as:

$$
K_y = \frac{N_{y,Known}}{N_{y,Known} + N_{y,Unknown}}
$$

The denominator here represents all records of individuals who joined KEV during that year. These values are stored as decimals and formatted as percentages when displayed. “Unknown” values cannot be considered negative evidence. Therefore, both the legend and the main text must use the official values or phrases like “Confirmed/Not Confirmed”. They cannot be replaced with phrases like “Ransomware Vulnerability/Non-Ransomware Vulnerability”. \(K_y \in [0,1]\)

### 3. Analysis of Manufacturer, Product, and Catalog Concentration (20 points)

#### (1) Create a summary table of manufacturers and products

Retain the original `vendorProject` and `product` fields. Use the `vendor_clean` and `product_clean` fields generated in step 1 for grouping. The cleaning process only removes leading and trailing spaces. No fuzzy matching is performed, and manufacturers with similar names are not merged arbitrarily. For each manufacturer, at least the following calculations are performed:

- Number of KEV records;
- Proportion of the total 1,656 records.
- Cumulative percentage;
- The amount of different `product_clean`

The manufacturers are sorted in a consistent manner based on “descending record count, ascending `vendor_clean`”. Then, they are grouped by “manufacturer + product”. A definitive sort must be performed first according to “descending record count, ascending `vendor_clean`, ascending `product_clean`” before using the `head(30)` function. It’s not allowed to directly extract the first 30 items from results where the order of ties isn’t specified. The “Multiple Products” in the attachment represent the original product names. These should be retained as a single text category and not split arbitrarily.

#### (2) Calculate concentration ratio

Let the proportion of records for each manufacturer be \(p_j\). Calculate the concentration ratio for the top 5 and top 10 manufacturers:

$$
CR_k = \sum_{j=1}^{k} p_j
$$

Also calculate the Herfindahl-Hirschman index without multiplying by 10,000:

$$
HHI = \sum_j p_j^2
$$

The concentration level mentioned here refers only to how concentrated the KEV directory records are across various manufacturer-specific text labels. It does not represent market share concentration, nor can it be used to determine which manufacturers are less secure. Factors such as a manufacturer’s product scale, market coverage, and the way in which data is disclosed and recorded all influence the number of records.

### 4. CWE Multi-tag Statistics and Combined Query Functions (20 points)

#### (1) Properly expand the CWE list

In the attachments, 1,485 records contain at least one CWE. For 171 records, the list of CWEs is empty. Among the records with CWEs, some CVEs correspond to multiple pieces of code. A long table was created using the `explode` function or equivalent methods, with each row representing a “CVE-CWE” correspondence.

For each CWE, count the number of different CVEs associated with that code. Do not count the same CVE multiple times based on the number of lines of code. The proportion of CWEs that appear in records with a CWE identifier is defined as follows:

$$
S_c = \frac{\#\{\text{Different CVE with }c\}}{1485}
$$

One CVE can contain multiple CWEs. Therefore, the sum of these values can exceed 1 (and exceed 100% when expressed as a percentage). It’s not possible to force these values to be mutually exclusive. Among the records in the attachment, 294 are “Known” and contain at least one CWE, while 1,191 are “Unknown” and contain at least one CWE. When calculating the proportion of CWEs in each subset, 294 and 1,191 should be used as the denominators respectively. This should be clearly indicated in the table header or captions. It’s not appropriate to divide by 1,485 overall, nor to divide by all 332 Known records or 1,324 Unknown records.

#### (2) Implementing composite query functions

Implement the function:

```python
filter_kev(df, start_date=None, end_date=None,
           vendor=None, ransomware=None, cwe=None)
```

Function requirements:

- The start and end dates are filtered using the `dateAdded` field as a closed interval.
- The vendor performs a case-insensitive substring match for `vendor_clean`.
- Ransomware only accepts the values “Known”, “Unknown”, or “None”. Any invalid value should trigger an exception.
- First, convert CWE to uppercase and check against the pattern `^CWE-[0-9]+$`. Then, perform an exact match based on the list members. Fuzzy matching is not allowed in the resulting long string.
- When multiple non-empty conditions are provided at the same time, the logical “AND” operator is used.
- Do not modify the original DataFrame that was passed in.
- Return `(result, summary)`: The result is a table sorted in descending order by `dateAdded` and ascending order by `cveID`. The summary includes at least the number of records, number of vendors, maximum date, and number of known issues. An empty result should still maintain the complete column structure, with the number of records, number of vendors, and number of known issues set to 0, and the maximum date left as a null value.

Design at least three sets of queries, covering different combinations of date criteria, vendor criteria, ransomware status, and CWE criteria. For each set, record the input parameters, number of rows returned, and a summary. Also, export the actual records; do not merely print the counts.

## IV. Instructions for Optional Sections

### 1. KEV Directory Search and Visualization GUI

Design the program using Tkinter, PyQt, or other Python GUI libraries to directly read the course JSON data. To avoid mistaking date strings and semicolon-separated text in the CSV file for already parsed dates and lists, the GUI should not use `kev_prepared.csv` as input. At a minimum, implement the following:

1. Select a file and view the directory version, release date, number of records, and loading status.
2. Filter by addition date, manufacturer or project, product keywords, Known/Unknown, and CWE. Also includes a reset function.
3. At least two of the monthly record charts, vendor record charts, or CWE charts should be updated in response to filtering criteria.
4. The table displays CVE results. When selected, details such as a brief description, required actions, due date, and notes are displayed.
5. Export the current filtered results as a CSV file and the current graph as a PNG file.

Referenced official materials:

- CISA KEV Catalog: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- CISA JSON Schema: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities_schema.json
- KEV CC0: https://www.cisa.gov/sites/default/files/licenses/kev/license.txt
- Pandas `json_normalize`: https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html
- Pandas `explode`: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.explode.html
- Plotly Treemap: https://plotly.com/python/treemaps/
