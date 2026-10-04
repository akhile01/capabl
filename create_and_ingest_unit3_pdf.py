import os
import requests
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_unit3_pdf(output_path: str):
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=12
    )
    
    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#2563eb'),
        spaceBefore=14,
        spaceAfter=8
    )

    h3_style = ParagraphStyle(
        'Heading3Custom',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )

    code_style = ParagraphStyle(
        'CodeCustom',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#09090b'),
        backColor=colors.HexColor('#f1f5f9'),
        spaceBefore=6,
        spaceAfter=8,
        borderPadding=6
    )

    story = []

    # Title & Overview
    story.append(Paragraph("Unit - 3: SQL Queries, Constraints, Triggers & Schema Refinement", title_style))
    story.append(Paragraph("<b>Syllabus Scope:</b> Form of basic SQL query, UNION, INTERSECT, and EXCEPT, Nested Queries, aggregation operators, NULL values, complex integrity constraints in SQL, triggers and active databases. Schema Refinement: Problems caused by redundancy, decompositions, reasoning about functional dependencies, Normal Forms (1NF, 2NF, 3NF, BCNF), lossless join decomposition, multivalued dependencies (4NF, 5NF).", body_style))
    story.append(Spacer(1, 14))

    # Section 1: Basic Form of an SQL Query
    story.append(Paragraph("1. Form of Basic SQL Query", h2_style))
    story.append(Paragraph("The basic form of an SQL query for data retrieval is composed of a combination of clauses:", body_style))
    story.append(Paragraph("<b>Syntax:</b><br/>SELECT [DISTINCT] column1, column2, ...<br/>FROM tablename<br/>WHERE condition;", code_style))
    story.append(Paragraph("<b>Core Clauses Explained:</b><br/>"
                           "• <b>SELECT Clause:</b> Specifies which columns to retrieve. Use asterisk (*) to retrieve all columns.<br/>"
                           "• <b>FROM Clause:</b> Specifies the source table or tables from which data is fetched.<br/>"
                           "• <b>WHERE Clause:</b> Predicate filter to restrict returned rows based on logical conditions.<br/>"
                           "• <b>DISTINCT Clause:</b> Optional keyword ensuring the result contains no duplicate tuples.<br/>"
                           "• <b>GROUP BY:</b> Groups rows sharing identical values in specified columns into summary rows.<br/>"
                           "• <b>HAVING:</b> Filters the groups created by GROUP BY.<br/>"
                           "• <b>ORDER BY:</b> Sorts returned records in ascending (ASC) or descending (DESC) order.<br/>"
                           "• <b>JOIN:</b> Combines fields from two or more tables using foreign key relationships.", body_style))
    story.append(Spacer(1, 10))

    # Section 2: Pattern Matching & Regular Expressions (LIKE)
    story.append(Paragraph("2. Pattern Matching with the LIKE Operator", h2_style))
    story.append(Paragraph("SQL supports pattern matching using the <b>LIKE</b> operator in the WHERE clause along with wildcards:", body_style))
    story.append(Paragraph("• <b>Percent sign (%):</b> Represents zero, one, or multiple arbitrary characters.<br/>"
                           "• <b>Underscore sign (_):</b> Represents exactly one single character.<br/>"
                           "<b>Examples:</b><br/>"
                           "• <code>SELECT FirstName FROM Customers WHERE FirstName LIKE 'Ma%';</code> (Names starting with 'Ma')<br/>"
                           "• <code>SELECT ProductName FROM Products WHERE ProductName LIKE '%ing';</code> (Products ending in 'ing')<br/>"
                           "• <code>SELECT BookTitle FROM Books WHERE BookTitle LIKE '%life%';</code> (Books containing 'life' anywhere)<br/>"
                           "• <code>SELECT Word FROM Words WHERE Word LIKE 'h_l__';</code> (5-letter words with 'h' at pos 1 and 'l' at pos 3)<br/>"
                           "• <code>SELECT column_name FROM table_name WHERE column_name LIKE 'A__o%';</code> (Starts with 'A', two characters, then 'o')", body_style))
    story.append(Spacer(1, 10))

    # Section 3: SQL Set Operations
    story.append(Paragraph("3. SQL Set Operations (UNION, INTERSECT, EXCEPT)", h2_style))
    story.append(Paragraph("Set operations combine the result sets of two or more SELECT queries. Requirement: The number of columns and compatible data types must match across participating queries.", body_style))
    story.append(Paragraph("• <b>UNION:</b> Combines query results and automatically removes duplicate rows.<br/>"
                           "• <b>UNION ALL:</b> Combines query results without removing duplicates or sorting, providing maximum execution performance.<br/>"
                           "• <b>INTERSECT:</b> Returns only tuples common to both queries (no duplicates, ordered ascending by default).<br/>"
                           "• <b>EXCEPT / MINUS:</b> Returns tuples present in the first query but absent in the second query.", body_style))
    story.append(Paragraph("<b>Syntax Example:</b><br/>SELECT column_name FROM table1 UNION SELECT column_name FROM table2;<br/>SELECT column_name FROM table1 INTERSECT SELECT column_name FROM table2;<br/>SELECT column_name FROM table1 EXCEPT SELECT column_name FROM table2;", code_style))
    story.append(Spacer(1, 10))

    # Section 4: Nested Queries
    story.append(Paragraph("4. Nested Queries: Independent and Correlated", h2_style))
    story.append(Paragraph("A nested query places an inner SELECT query inside an outer query's WHERE or HAVING clause.", body_style))
    story.append(Paragraph("<b>A. Independent Nested Queries:</b><br/>"
                           "Execution flows strictly from the innermost query to the outer query. The inner query executes once and passes its result set to the outer query.<br/>"
                           "• <b>IN:</b> Matches when the column value equals any element in the subquery result.<br/>"
                           "• <b>NOT IN:</b> Matches when the column value is absent from the subquery result.<br/>"
                           "• <b>ALL:</b> Evaluates to TRUE only if comparison holds against every single value returned.<br/>"
                           "• <b>ANY / SOME:</b> Evaluates to TRUE if comparison holds against at least one value returned.<br/>"
                           "<i>Example:</i> <code>SELECT * FROM employees WHERE salary > ALL (SELECT salary FROM employees WHERE role = 'Manager');</code>", body_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>B. Correlated (Co-related) Nested Queries:</b><br/>"
                           "The inner query references column values from the current outer row (e.g. <code>emp1.role = emp2.role</code>). The inner query must re-evaluate for <i>every single row</i> considered by the outer query, making execution time proportional to the outer table size.<br/>"
                           "<i>Example:</i> <code>SELECT * FROM employees emp1 WHERE salary > (SELECT AVG(salary) FROM employees emp2 WHERE emp1.role = emp2.role);</code>", body_style))
    story.append(Spacer(1, 10))

    # Section 5: Aggregate Functions
    story.append(Paragraph("5. SQL Aggregate Functions", h2_style))
    story.append(Paragraph("Aggregate functions compute mathematical summaries over multiple column values and return a single scalar value:<br/>"
                           "• <b>COUNT(*):</b> Returns total number of rows, including duplicates and NULL values.<br/>"
                           "• <b>COUNT(column):</b> Returns count of non-NULL values.<br/>"
                           "• <b>COUNT(DISTINCT column):</b> Returns count of unique non-NULL values.<br/>"
                           "• <b>SUM(column):</b> Calculates arithmetic sum of numeric values (ignores NULLs).<br/>"
                           "• <b>AVG(column):</b> Calculates arithmetic mean of non-NULL numeric values.<br/>"
                           "• <b>MAX(column) & MIN(column):</b> Return highest and lowest values respectively.<br/>"
                           "<i>Grouping:</i> Combined with <code>GROUP BY</code> to produce group totals and <code>HAVING</code> to filter aggregated results (e.g., <code>HAVING COUNT(*) > 2</code>).", body_style))
    story.append(Spacer(1, 10))

    # Section 6: NULL Values
    story.append(Paragraph("6. NULL Values in Relational Databases", h2_style))
    story.append(Paragraph("NULL represents missing, inapplicable, or withheld information. Key principles:<br/>"
                           "• NULL is distinct from numerical 0 and empty character strings ('').<br/>"
                           "• Arithmetic expressions involving NULL evaluate to NULL (e.g., <code>10 + NULL = NULL</code>).<br/>"
                           "• Equality operators (<code>= NULL</code> or <code>!= NULL</code>) cannot be used because each NULL is considered distinct. Comparisons must use <b>IS NULL</b> or <b>IS NOT NULL</b>.<br/>"
                           "• In unique and foreign key constraints, NULLs receive special handling (e.g. primary keys strictly disallow NULLs under Entity Integrity).<br/>"
                           "• Updating NULLs: <code>UPDATE Employee SET SSN = '789-01-2345' WHERE SSN IS NULL;</code>", body_style))
    story.append(Spacer(1, 10))

    # Section 7: Complex Integrity Constraints & Triggers
    story.append(Paragraph("7. Complex Integrity Constraints & Active Databases", h2_style))
    story.append(Paragraph("<b>CHECK Constraints:</b> Enforce domain-level restrictions via logical predicates (e.g. <code>Age INT CHECK (Age >= 18 AND Age <= 30)</code> or email pattern checks).<br/>"
                           "<b>Composite Keys:</b> Primary or foreign key constraints spanning multiple columns.<br/>"
                           "<b>Active Databases & Triggers:</b><br/>"
                           "An active database incorporates reactive behavior into the DBMS using <b>ECA (Event-Condition-Action)</b> rules:<br/>"
                           "• <b>Event:</b> A database modification statement that activates the trigger (INSERT, UPDATE, DELETE).<br/>"
                           "• <b>Condition:</b> An optional boolean check (WHEN clause) verified before action executes.<br/>"
                           "• <b>Action:</b> The procedure or statement executed when the trigger fires.<br/>"
                           "<b>Classification of Triggers:</b><br/>"
                           "• <b>Statement-Level Trigger:</b> Fires exactly once per DML statement regardless of how many rows are modified (default).<br/>"
                           "• <b>Row-Level Trigger (FOR EACH ROW):</b> Fires once for each individual row modified, providing access to <code>:NEW</code> and <code>:OLD</code> values.<br/>"
                           "• <b>BEFORE Trigger:</b> Fires before data modifications are written to disk; used to validate data, enforce constraints, or compute defaults.<br/>"
                           "• <b>AFTER Trigger:</b> Fires after changes are applied; commonly used for auditing, external notification, and replica updates.<br/>"
                           "• <b>Recursive Triggers:</b> Triggers whose actions invoke events that re-activate the same or other triggers in a chain.", body_style))
    story.append(Spacer(1, 10))

    # Section 8: Schema Refinement & Normalization
    story.append(Paragraph("8. Schema Refinement & Redundancy Anomalies", h2_style))
    story.append(Paragraph("Schema refinement decomposes unnormalized schemas to eliminate data redundancy and preserve integrity.<br/>"
                           "<b>Problems Caused by Redundancy:</b><br/>"
                           "• <b>Insertion Anomaly:</b> Inability to record certain facts without inserting unrelated dummy or null data.<br/>"
                           "• <b>Deletion Anomaly:</b> Unintended loss of crucial information when deleting an unrelated tuple.<br/>"
                           "• <b>Updation Anomaly:</b> Inconsistency arising when redundant copies of a data item are updated in some rows but not others.<br/>"
                           "<b>Normal Forms Overview:</b><br/>"
                           "• <b>1NF:</b> Atomic column values; no repeating groups.<br/>"
                           "• <b>2NF:</b> In 1NF and no partial dependencies (every non-prime attribute fully functionally dependent on whole candidate key).<br/>"
                           "• <b>3NF:</b> In 2NF and no transitive functional dependencies.<br/>"
                           "• <b>BCNF (Boyce-Codd NF):</b> For every non-trivial functional dependency X -> Y, X must be a superkey.<br/>"
                           "• <b>Lossless-Join Decomposition:</b> Ensures natural join of decomposed relations exactly reconstructs the original relation without spurious tuples.", body_style))

    doc.build(story)
    print(f"Successfully generated PDF at: {output_path}")

if __name__ == "__main__":
    out = os.path.abspath("Unit_3_SQL_Queries_Constraints_Triggers_Schema_Refinement.pdf")
    create_unit3_pdf(out)
    
    # Now ingest via API
    url = "http://127.0.0.1:8000/api/ingest"
    with open(out, "rb") as f:
        files = {"file": (os.path.basename(out), f, "application/pdf")}
        data = {
            "subject": "Database Systems",
            "chapter": "Unit 3 — SQL Queries, Constraints, Triggers & Schema Refinement"
        }
        res = requests.post(url, files=files, data=data)
        print("Ingestion API response:", res.status_code, res.text)
