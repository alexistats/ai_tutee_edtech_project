"""Assessment module for generating and evaluating pre/post tests for AI tutee.

Uses multiple choice questions (MCQ) that can be programmatically graded.
"""

from typing import Dict, List, Tuple
import os
import json
from openai import OpenAI


# Multiple Choice Assessment Questions organized by scenario and knowledge level
MCQ_ASSESSMENT = {
    "data_types": {
        "beginner": [
        {
            "question": "A dataset contains a column 'ProductID' with values like 1001, 1002, 1003. What type of data is this?",
            "options": {
                "A": "Continuous numerical data",
                "B": "Discrete numerical data for calculations",
                "C": "Categorical identifier (nominal)",
                "D": "Ordinal data"
            },
            "correct_answer": "C",
            "explanation": "ProductID is a categorical identifier (nominal data), not quantitative. Even though it uses numbers, it represents categories and should not be used in calculations."
        },
        {
            "question": "Survey responses range from 'Strongly Disagree' (1) to 'Strongly Agree' (5). What is the MOST important consideration when visualizing this data?",
            "options": {
                "A": "It's continuous data, so use a line chart",
                "B": "It's ordinal data with meaningful order but unequal intervals",
                "C": "It's nominal categorical data with no order",
                "D": "It's discrete numerical data suitable for any calculation"
            },
            "correct_answer": "B",
            "explanation": "Likert scale data is ordinal - it has a meaningful order, but the intervals between values aren't necessarily equal, so treat it differently than continuous numerical data."
        },
        {
            "question": "Which of the following is an example of continuous numerical data?",
            "options": {
                "A": "Number of employees in a company (e.g., 50, 51, 52)",
                "B": "Temperature readings (e.g., 72.3°F, 72.5°F, 72.7°F)",
                "C": "T-shirt sizes (Small, Medium, Large)",
                "D": "Customer satisfaction rating (1-5 stars)"
            },
            "correct_answer": "B",
            "explanation": "Temperature is continuous because it can take any value within a range. Employee count is discrete (can't have 50.5 employees), and the others are categorical."
        },
        {
            "question": "You have a 'signup_date' column with values like '2024-01-15', '2024-02-20'. What type of data is this?",
            "options": {
                "A": "Nominal categorical",
                "B": "Ordinal categorical",
                "C": "Temporal (time-based) data",
                "D": "Continuous numerical"
            },
            "correct_answer": "C",
            "explanation": "Dates are temporal data - they have chronological order and are often used to show trends over time."
        },
        {
            "question": "A dataset has department codes: 101=Sales, 102=Marketing, 103=Engineering. How should you treat these codes?",
            "options": {
                "A": "As continuous numbers for mathematical operations",
                "B": "As nominal categorical labels, not for calculations",
                "C": "As ordinal data showing department hierarchy",
                "D": "As discrete numerical data for averaging"
            },
            "correct_answer": "B",
            "explanation": "Department codes are nominal categorical identifiers. The numbers are just labels and shouldn't be used in calculations (averaging departments makes no sense)."
        }
        ],
        "intermediate": [
            {
                "question": "A dataset contains 'customer_age' (23, 45, 67) and 'age_group' ('18-30', '31-50', '51+'). How should you handle these for analysis?",
                "options": {
                    "A": "Treat both as continuous numerical data",
                    "B": "customer_age is continuous numerical, age_group is ordinal categorical",
                    "C": "Both are ordinal categorical",
                    "D": "customer_age is discrete numerical, age_group is nominal categorical"
                },
                "correct_answer": "B",
                "explanation": "customer_age is continuous numerical (can take any value in range). age_group is ordinal categorical (ordered categories but not numeric). Understanding these differences is crucial for choosing appropriate visualizations."
            },
            {
                "question": "ZIP codes (90210, 10001) appear numeric but should be treated as:",
                "options": {
                    "A": "Continuous data for regression analysis",
                    "B": "Discrete numerical data for calculations",
                    "C": "Nominal categorical data (identifiers)",
                    "D": "Ordinal data with geographic ordering"
                },
                "correct_answer": "C",
                "explanation": "ZIP codes are nominal categorical identifiers. While they appear numeric, performing arithmetic operations (averaging ZIP codes) is meaningless. They represent geographic regions as labels."
            },
            {
                "question": "You have 'satisfaction_score' (1-10 scale). When is it appropriate to treat this as continuous vs ordinal?",
                "options": {
                    "A": "Always treat as continuous since it's numeric",
                    "B": "Treat as ordinal for visualizations, but continuous for statistical analysis if intervals are approximately equal",
                    "C": "Always treat as ordinal since it's rating data",
                    "D": "Treat as nominal since numbers are just labels"
                },
                "correct_answer": "B",
                "explanation": "Rating scales (especially 1-10) can be treated as continuous if you assume equal intervals between values. However, for visualizations, acknowledging the ordinal nature (discrete steps) often provides clearer communication."
            },
            {
                "question": "A 'revenue' column has values like '$1.5M', '$3.2M', '$850K'. What's the FIRST data quality issue?",
                "options": {
                    "A": "The data is categorical, not numerical",
                    "B": "Mixed units (millions vs thousands) and text formatting prevent numerical operations",
                    "C": "The data is temporal, not numerical",
                    "D": "The data should be ordinal, not continuous"
                },
                "correct_answer": "B",
                "explanation": "This is a data type casting issue. The values need to be parsed: convert 'M' to millions, 'K' to thousands, remove '$', then cast to numeric type. Only then can you perform calculations or create numerical visualizations."
            },
            {
                "question": "When dealing with timestamps ('2024-01-15 14:30:00'), you can extract multiple data types. Which is NOT a valid extraction?",
                "options": {
                    "A": "Date (temporal) - '2024-01-15'",
                    "B": "Hour of day (discrete numerical or ordinal) - 14",
                    "C": "Day of week (ordinal or nominal) - 'Monday'",
                    "D": "Timestamp average (continuous) for trend analysis"
                },
                "correct_answer": "D",
                "explanation": "You cannot meaningfully average timestamps. You can extract components (date, hour, day) or calculate durations, but averaging timestamps directly is statistically invalid. Each extracted component has its own data type."
            }
        ],
        "advanced": [
            {
                "question": "You have 'income' data with extreme right skew (few very high earners). How does this affect data type classification and visualization choice?",
                "options": {
                    "A": "Income becomes ordinal due to skew; use bar charts",
                    "B": "Income remains continuous, but consider log transformation or binning to ordinal categories for clearer visualization",
                    "C": "Income becomes categorical; use pie charts",
                    "D": "Skew doesn't affect data type, only visualization aesthetics"
                },
                "correct_answer": "B",
                "explanation": "Data type is inherent to the variable, not its distribution. However, extreme skew in continuous data may warrant transformation (log scale) or binning into ordinal categories (income brackets) for better visualization and interpretation."
            },
            {
                "question": "A dataset has 'education_years' (12, 14, 16, 18) and 'education_level' (High School, Associate, Bachelor, Graduate). Which statement is most accurate?",
                "options": {
                    "A": "education_years is continuous, education_level is nominal - they measure different things",
                    "B": "Both are discrete numerical since education_years uses numbers",
                    "C": "education_years is discrete numerical (ratio scale), education_level is ordinal - they represent the same concept differently",
                    "D": "education_years is ordinal, education_level is nominal - no relationship"
                },
                "correct_answer": "C",
                "explanation": "education_years is discrete numerical (ratio scale: 16 years is truly twice 8 years). education_level is ordinal (ordered but unequal intervals: Bachelor to Graduate ≠ High School to Associate). They encode the same concept with different properties."
            },
            {
                "question": "When is it appropriate to convert continuous data (temperature: 72.3°F) to ordinal categories (Cold, Mild, Hot)?",
                "options": {
                    "A": "Never - you lose information and precision",
                    "B": "When the audience needs actionable categories (What should I wear?) rather than precise values",
                    "C": "Always - categorical data is easier to visualize",
                    "D": "Only when you have missing data"
                },
                "correct_answer": "B",
                "explanation": "Binning continuous to ordinal is a trade-off: you lose precision but gain interpretability. It's appropriate when categorical decisions are needed (Cold→wear jacket) or when precise values add noise rather than insight. Context determines the right choice."
            },
            {
                "question": "You have 'response_time' in milliseconds with bimodal distribution (fast automated responses ~100ms, slow human responses ~5000ms). How should you handle this for visualization?",
                "options": {
                    "A": "Treat as continuous and use histogram - distribution shape is important",
                    "B": "Convert to binary categorical (automated vs human) - the two modes represent different processes",
                    "C": "Use log scale transformation to compress the range",
                    "D": "Either A or B depending on analytical goal - both preserve important information"
                },
                "correct_answer": "D",
                "explanation": "This is a nuanced decision. If analyzing distribution patterns, continuous histogram (possibly with log scale) works. If the goal is comparing process types, categorical split is clearer. Advanced practitioners choose based on the analytical question, not rigid rules."
            },
            {
                "question": "A 'priority' field uses values 'P0', 'P1', 'P2', 'P3' where P0=critical, P3=low. What's the most sophisticated handling?",
                "options": {
                    "A": "Nominal categorical - they're just labels",
                    "B": "Ordinal categorical with explicit ordering (P0>P1>P2>P3) for proper sorting in visualizations",
                    "C": "Convert to numerical (0,1,2,3) for mathematical operations",
                    "D": "Binary categorical (Critical vs Non-Critical)"
                },
                "correct_answer": "B",
                "explanation": "Priority is ordinal with specific ordering. Keep as ordinal categorical but define explicit sort order for visualizations. Converting to numerical (option C) implies equal intervals which is false. Maintaining ordinal type with proper ordering preserves semantic meaning while enabling correct sorting."
            }
        ]
    },
    "type_to_chart": {
        "beginner": [
        {
            "question": "You need to compare quarterly revenue across 5 product categories. Which chart is MOST appropriate?",
            "options": {
                "A": "Line chart",
                "B": "Scatter plot",
                "C": "Bar chart or column chart",
                "D": "Pie chart"
            },
            "correct_answer": "C",
            "explanation": "Bar/column charts are ideal for comparing numerical values across discrete categories. Each category gets its own bar, making comparison easy."
        },
        {
            "question": "When is a line chart preferred over a bar chart?",
            "options": {
                "A": "When comparing discrete categories like product types",
                "B": "When showing trends over time or continuous data",
                "C": "When showing composition of a whole",
                "D": "When displaying the relationship between two numerical variables"
            },
            "correct_answer": "B",
            "explanation": "Line charts are best for temporal data or continuous data where the connection between points is meaningful, showing trends and patterns."
        },
        {
            "question": "You have two numerical variables: employee age and salary. Which chart type would best show their relationship?",
            "options": {
                "A": "Pie chart",
                "B": "Bar chart",
                "C": "Line chart",
                "D": "Scatter plot"
            },
            "correct_answer": "D",
            "explanation": "Scatter plots are designed to show relationships between two numerical variables and can reveal correlations or patterns."
        },
        {
            "question": "A pie chart is most appropriate when you want to:",
            "options": {
                "A": "Show trends over time",
                "B": "Compare many categories (10+)",
                "C": "Display parts of a whole (composition)",
                "D": "Show correlation between variables"
            },
            "correct_answer": "C",
            "explanation": "Pie charts show composition - how parts make up a whole. They work best with few categories (3-7) to show proportions."
        },
        {
            "question": "You have monthly sales data for 12 months. Which chart would be LEAST appropriate?",
            "options": {
                "A": "Line chart showing the trend",
                "B": "Bar chart showing monthly values",
                "C": "Pie chart with 12 slices for each month",
                "D": "Area chart showing cumulative sales"
            },
            "correct_answer": "C",
            "explanation": "A pie chart is least appropriate because months don't represent parts of a whole - they're sequential time periods better shown with line or bar charts."
        }
        ],
        "intermediate": [
            {
                "question": "You need to compare sales across 3 regions AND show trend over 12 months. Which chart handles both dimensions best?",
                "options": {
                    "A": "Single line chart with 3 lines (one per region)",
                    "B": "Grouped bar chart with months on x-axis and grouped bars per region",
                    "C": "Three separate pie charts (one per region)",
                    "D": "Either A or B depending on whether trend or comparison is more important"
                },
                "correct_answer": "D",
                "explanation": "Multi-line chart emphasizes trends and makes time-based patterns clear. Grouped bar chart emphasizes categorical comparison at each time point. The choice depends on your analytical priority - both are valid for different insights."
            },
            {
                "question": "When would you choose a heatmap over a scatter plot for numerical data?",
                "options": {
                    "A": "Never - scatter plots are always better for numerical data",
                    "B": "When you have 3 variables (x, y, and color-encoded value) and want to show patterns across a grid",
                    "C": "Only for categorical data",
                    "D": "When you have less than 10 data points"
                },
                "correct_answer": "B",
                "explanation": "Heatmaps excel when you have grid-structured data (like time x category) with a third numerical variable encoded as color. Scatter plots work for 2D relationships. Each serves different purposes based on data structure."
            },
            {
                "question": "Your data includes 'country' (categorical) and 'population' (numerical). What additional context determines chart choice?",
                "options": {
                    "A": "Chart choice is fixed: always use bar chart for categorical vs numerical",
                    "B": "Number of countries matters: bar chart for <20 countries, treemap for many, map for geographic patterns",
                    "C": "Only the data types matter",
                    "D": "Always use pie chart for population data"
                },
                "correct_answer": "B",
                "explanation": "Data type alone doesn't determine chart choice. Consider: How many categories? (too many for bar chart?), Is geography important? (use map), Is hierarchy present? (treemap). Context and analytical goal matter as much as data type."
            },
            {
                "question": "For showing correlation between 10+ numerical variables simultaneously, which is most effective?",
                "options": {
                    "A": "10+ separate scatter plots",
                    "B": "Correlation matrix heatmap",
                    "C": "Single line chart with 10 lines",
                    "D": "Stacked bar chart"
                },
                "correct_answer": "B",
                "explanation": "Correlation matrix heatmap efficiently shows pairwise relationships between many numerical variables using color encoding. Scatter plot matrix is an alternative, but heatmap is more compact for identifying correlation patterns quickly."
            },
            {
                "question": "You have temporal data at different granularities (hourly, daily, monthly). How does this affect chart choice?",
                "options": {
                    "A": "Always use line chart regardless of granularity",
                    "B": "Hourly→line chart, Daily→bar chart, Monthly→pie chart",
                    "C": "Granularity determines point density: hourly (line for trends), daily (line or bar), monthly (bar if comparing months, line if showing trend)",
                    "D": "Temporal data always requires area charts"
                },
                "correct_answer": "C",
                "explanation": "Granularity affects visual density and analytical focus. High frequency (hourly) works best as line to show continuous flow. Lower frequency (monthly) can use bars if emphasizing discrete comparisons, or lines if emphasizing trend. Match chart to analytical goal and data density."
            }
        ],
        "advanced": [
            {
                "question": "You need to visualize 5 dimensions: time, region, product category, sales volume, and profit margin. What's the most sophisticated approach?",
                "options": {
                    "A": "Impossible - limit to 3 dimensions maximum",
                    "B": "Animated scatter plot: x=time, y=sales, color=profit margin, shape=product, size=region count, animation=time",
                    "C": "Multiple coordinated charts: line chart (time × sales) + small multiples by region + color for profit margin",
                    "D": "Single 3D bar chart"
                },
                "correct_answer": "C",
                "explanation": "Advanced visualization handles high dimensionality through coordination and faceting, not cramming into one chart. Small multiples, coordinated views, and thoughtful encoding (color, size) are more effective than complex single charts. Option B overloads a single chart."
            },
            {
                "question": "When is a violin plot preferred over a box plot for distribution visualization?",
                "options": {
                    "A": "Never - box plots are always superior",
                    "B": "When you need to show full distribution shape (bimodal, skewness) beyond quartiles",
                    "C": "Only for categorical data",
                    "D": "When you have less than 10 data points"
                },
                "correct_answer": "B",
                "explanation": "Violin plots show the full probability density function, revealing bimodality and distribution shape that box plots hide. Box plots show quartiles concisely. Choose violin when distribution shape matters, box plot for quick quartile comparison."
            },
            {
                "question": "You're visualizing hierarchical data (Company → Department → Team → Individual). Which chart type is LEAST appropriate?",
                "options": {
                    "A": "Treemap (nested rectangles sized by metric)",
                    "B": "Sunburst chart (nested circles)",
                    "C": "Scatter plot",
                    "D": "Hierarchical edge bundling or dendrogram"
                },
                "correct_answer": "C",
                "explanation": "Scatter plots show relationships between two continuous variables, not hierarchy. Treemaps, sunbursts, and dendrograms are specifically designed for hierarchical data, using nesting or tree structures to encode parent-child relationships."
            },
            {
                "question": "For real-time streaming data (stock prices updating every second), what chart design consideration is most critical?",
                "options": {
                    "A": "Color scheme",
                    "B": "Update mechanism (sliding window, aggregation) to prevent visual overload and maintain context",
                    "C": "Chart type doesn't matter for streaming data",
                    "D": "Always show all historical data"
                },
                "correct_answer": "B",
                "explanation": "Streaming data requires careful temporal window management: sliding windows (last N minutes), aggregation (1-minute averages), or zoom/pan controls. Showing all data causes clutter; dropping context loses trends. Advanced streaming viz balances real-time updates with historical context."
            },
            {
                "question": "You have highly skewed data (power law distribution) and want to show both overall pattern and detail. Best approach?",
                "options": {
                    "A": "Single linear-scale chart - shows true data",
                    "B": "Log-scale transformation on relevant axis",
                    "C": "Separate charts: one log-scale (overall pattern) + one linear-scale with detail inset or filtering",
                    "D": "Remove outliers to force normal distribution"
                },
                "correct_answer": "C",
                "explanation": "Power law data (wealth, city sizes, word frequency) spans many orders of magnitude. Log scale reveals overall pattern but obscures small values. Linear scale shows detail but compresses most data. Advanced approach: use both views or log-scale with interactive detail-on-demand. Never remove outliers (option D) - they ARE the pattern in power law data."
            }
        ]
    },
    "chart_to_task": {
        "beginner": [
        {
            "question": "Your analytical task is to 'identify trends in website traffic over the past year'. Which chart type best matches this task?",
            "options": {
                "A": "Bar chart",
                "B": "Pie chart",
                "C": "Line chart",
                "D": "Scatter plot"
            },
            "correct_answer": "C",
            "explanation": "Line charts are ideal for trend analysis over time. They clearly show how values change and make patterns like growth or seasonality visible."
        },
        {
            "question": "You need to 'compare market share among 5 competitors'. Which chart best supports this task?",
            "options": {
                "A": "Line chart",
                "B": "Scatter plot",
                "C": "Pie chart or stacked bar chart",
                "D": "Histogram"
            },
            "correct_answer": "C",
            "explanation": "Market share is about composition (parts of a whole). Pie charts or 100% stacked bar charts effectively show how the total market is divided."
        },
        {
            "question": "The task is to 'understand the distribution of test scores in a class'. Which chart is most appropriate?",
            "options": {
                "A": "Pie chart",
                "B": "Line chart",
                "C": "Histogram or box plot",
                "D": "Scatter plot"
            },
            "correct_answer": "C",
            "explanation": "Histograms show distributions of continuous data by grouping values into bins. Box plots also show distribution with quartiles and outliers."
        },
        {
            "question": "Your task is to 'find the correlation between advertising spend and sales revenue'. Best visualization?",
            "options": {
                "A": "Two separate pie charts",
                "B": "Scatter plot with trendline",
                "C": "Stacked bar chart",
                "D": "Multiple line charts"
            },
            "correct_answer": "B",
            "explanation": "Scatter plots are designed to show relationships between two numerical variables. A trendline can confirm correlation strength."
        },
        {
            "question": "You need to 'show how budget is allocated across 8 departments'. Which task is this, and which chart fits best?",
            "options": {
                "A": "Trend analysis - use line chart",
                "B": "Comparison - use bar chart",
                "C": "Correlation - use scatter plot",
                "D": "Distribution - use histogram"
            },
            "correct_answer": "B",
            "explanation": "Budget allocation across departments is a comparison task. Bar charts excel at comparing values across multiple categories."
        }
        ],
        "intermediate": [
            {
                "question": "Your task is to 'identify outliers and their impact on overall metrics'. Which visualization best supports this?",
                "options": {
                    "A": "Pie chart",
                    "B": "Box plot or scatter plot with statistical boundaries (±2 SD or IQR)",
                    "C": "Line chart",
                    "D": "Stacked bar chart"
                },
                "correct_answer": "B",
                "explanation": "Outlier identification requires showing distribution and boundaries. Box plots display quartiles and outliers explicitly. Scatter plots with statistical boundaries (standard deviation or IQR lines) also highlight unusual points effectively."
            },
            {
                "question": "You need to 'compare actual vs. target sales across 10 product lines'. What chart handles this comparison task best?",
                "options": {
                    "A": "Bullet chart or grouped bar chart (actual vs target per product)",
                    "B": "Single line chart",
                    "C": "Pie chart",
                    "D": "Histogram"
                },
                "correct_answer": "A",
                "explanation": "Comparing actual vs. target requires showing both values per category. Bullet charts are designed for this (showing actual, target, and quality ranges). Grouped bar charts also work well, with bars grouped by product showing actual vs. target side-by-side."
            },
            {
                "question": "The task is 'understand customer journey through 5 sequential steps with dropout rates'. Which visualization fits best?",
                "options": {
                    "A": "Pie chart",
                    "B": "Funnel chart or Sankey diagram",
                    "C": "Scatter plot",
                    "D": "Box plot"
                },
                "correct_answer": "B",
                "explanation": "Sequential flow with dropout requires funnel charts (showing narrowing at each stage) or Sankey diagrams (showing flow quantities between stages). Both are purpose-built for conversion/journey analysis."
            },
            {
                "question": "Your task is 'explore relationships between multiple variables to generate hypotheses'. Best approach?",
                "options": {
                    "A": "Single bar chart",
                    "B": "Scatter plot matrix (SPLOM) or parallel coordinates",
                    "C": "Pie chart",
                    "D": "Single line chart"
                },
                "correct_answer": "B",
                "explanation": "Exploratory analysis of multiple variables requires multivariate visualization. Scatter plot matrix shows all pairwise relationships. Parallel coordinates show patterns across many dimensions. Both support hypothesis generation through pattern discovery."
            },
            {
                "question": "The task is 'track progress toward annual goal over time with context of previous years'. Which chart provides best context?",
                "options": {
                    "A": "Single line chart for current year only",
                    "B": "Line chart with current year highlighted and previous years as reference lines or shaded range",
                    "C": "Pie chart",
                    "D": "Histogram"
                },
                "correct_answer": "B",
                "explanation": "Progress tracking requires temporal context. Showing current year prominently with previous years as reference (lighter lines or shaded range) enables comparison to historical patterns and realistic goal assessment."
            }
        ],
        "advanced": [
            {
                "question": "Your stakeholder asks: 'Why did revenue drop in Q3?' What type of analysis and visualization best answers this diagnostic question?",
                "options": {
                    "A": "Single pie chart of Q3 revenue breakdown",
                    "B": "Drill-down analysis: line chart (overall trend) + decomposition (by region/product) + correlation analysis with external factors",
                    "C": "Bar chart of Q3 vs Q2",
                    "D": "Histogram of Q3 transactions"
                },
                "correct_answer": "B",
                "explanation": "Diagnostic questions (Why?) require multi-level analysis. Start with trend confirmation (line chart), decompose by dimensions (which region/product dropped?), and correlate with external factors (seasonality, competition, economy). One chart can't answer 'why' - you need analytical depth."
            },
            {
                "question": "The task is 'enable users to explore data themselves and answer their own questions'. What approach is most appropriate?",
                "options": {
                    "A": "Single static chart",
                    "B": "Interactive dashboard with filters, drill-down, and coordinated views",
                    "C": "PDF report with fixed charts",
                    "D": "Pie chart"
                },
                "correct_answer": "B",
                "explanation": "Self-service exploration requires interactivity: filters (select subsets), drill-down (see details), linked views (selections propagate). Static charts answer pre-defined questions; interactive dashboards empower users to ask their own questions and discover insights."
            },
            {
                "question": "You're visualizing A/B test results. The task is 'determine if the difference is statistically significant'. What must your visualization include?",
                "options": {
                    "A": "Just show the mean values in a bar chart",
                    "B": "Show means with confidence intervals, sample sizes, and ideally p-value or effect size",
                    "C": "Pie chart of conversion rates",
                    "D": "Line chart"
                },
                "correct_answer": "B",
                "explanation": "Statistical significance requires showing uncertainty. Display means with confidence intervals (error bars), note sample sizes (affects CI width), and include statistical test results (p-value, effect size). Bar chart without uncertainty is incomplete - overlapping CIs suggest no significant difference."
            },
            {
                "question": "Task: 'Identify which factors most influence customer churn.' What analytical visualization is most appropriate?",
                "options": {
                    "A": "Simple bar chart of churn rate",
                    "B": "Feature importance chart from predictive model + conditional distributions of top factors by churn status",
                    "C": "Pie chart of churned vs retained",
                    "D": "Single scatter plot"
                },
                "correct_answer": "B",
                "explanation": "Identifying drivers requires statistical analysis, not just description. Build a predictive model (logistic regression, random forest), visualize feature importance (which factors matter most), then show how those factors distribute differently for churned vs. retained customers. This combines machine learning with explanatory visualization."
            },
            {
                "question": "Your task involves multiple audiences: executives (high-level), analysts (detailed). Best approach?",
                "options": {
                    "A": "Single complex chart for everyone",
                    "B": "Separate deliverables or layered design: executive summary (KPIs, trends) + detailed appendix (distributions, segments)",
                    "C": "Only show detailed charts - executives can ignore what they don't need",
                    "D": "Only show high-level - analysts can request details separately"
                },
                "correct_answer": "B",
                "explanation": "Different audiences have different analytical needs. Advanced practice: create layered deliverables (executive dashboard → analyst workbooks) or progressive disclosure (summary → drill-down). One-size-fits-all satisfies no one. Tailor depth and detail to audience analytical sophistication and decision needs."
            }
        ]
    },
    "data_preparation": {
        "beginner": [
        {
            "question": "Your date column has mixed formats: '01/15/2024', '2024-02-20', '03-MAR-2024'. What should you do FIRST?",
            "options": {
                "A": "Delete all rows with inconsistent formats",
                "B": "Standardize all dates to a single format",
                "C": "Use them as-is; visualization tools will handle it",
                "D": "Convert them all to categorical data"
            },
            "correct_answer": "B",
            "explanation": "Standardizing date formats is critical for proper sorting and time-based analysis. Inconsistent formats will cause errors in temporal visualizations."
        },
        {
            "question": "You have a revenue column with 15% missing values. Which approach is LEAST appropriate?",
            "options": {
                "A": "Remove rows with missing revenue if the dataset is large enough",
                "B": "Impute with median revenue if values are missing at random",
                "C": "Replace all missing values with zero",
                "D": "Mark missing values as a separate category if missingness is meaningful"
            },
            "correct_answer": "C",
            "explanation": "Replacing missing values with zero is dangerous because it assumes zero revenue, which may not be true. Zero is a meaningful value, not 'missing'."
        },
        {
            "question": "Your data has one row per transaction (1000 rows). You want a bar chart of monthly sales. What data preparation is needed?",
            "options": {
                "A": "No preparation needed; use raw transaction data",
                "B": "Aggregate transactions by month and sum sales",
                "C": "Filter to show only the first transaction per month",
                "D": "Convert all dates to categorical months"
            },
            "correct_answer": "B",
            "explanation": "You need to aggregate (group) transaction-level data by month and sum the sales to get monthly totals suitable for visualization."
        },
        {
            "question": "You notice extreme outliers in your salary data (e.g., CEO salary is 50x the median). Before visualizing, you should:",
            "options": {
                "A": "Always remove all outliers automatically",
                "B": "Investigate whether outliers are errors or legitimate extreme values",
                "C": "Change all outliers to the median value",
                "D": "Ignore them; they won't affect the visualization"
            },
            "correct_answer": "B",
            "explanation": "Outliers could be data errors OR legitimate extreme values (like CEO salary). Investigate first - don't automatically remove or modify without understanding why they exist."
        },
        {
            "question": "Your dataset has a 'price' column stored as text: '$1,234.56'. Before creating a histogram, you need to:",
            "options": {
                "A": "Use it as-is; it's already numeric",
                "B": "Convert to categorical data",
                "C": "Remove '$' and ',' symbols, then convert to numeric type",
                "D": "Delete the column and recreate it"
            },
            "correct_answer": "C",
            "explanation": "Text-formatted numbers must be cleaned (remove currency symbols, commas) and type-cast to numeric for mathematical operations and proper visualization."
        }
        ],
        "intermediate": [
            {
                "question": "You have sales data with timestamps but need daily aggregates. However, some days have no transactions. How should you handle missing days?",
                "options": {
                    "A": "Ignore missing days - they'll just appear as gaps",
                    "B": "Create complete date range and fill missing days with 0 or explicit 'No Data' marker depending on meaning",
                    "C": "Delete the entire dataset",
                    "D": "Replace all dates with categories"
                },
                "correct_answer": "B",
                "explanation": "Missing dates in time series can be misleading. Generate a complete date sequence and fill missing days appropriately: $0 sales if no transactions is valid, or mark as 'No Data' if absence indicates data quality issue. Choice depends on domain meaning."
            },
            {
                "question": "Your dataset has a 'comments' text field. Before visualization, what preparation is needed to extract insights?",
                "options": {
                    "A": "Text can't be visualized - delete the column",
                    "B": "Extract features: length, sentiment, keywords, categories through NLP, then visualize those derived metrics",
                    "C": "Visualize the raw text directly",
                    "D": "Convert all text to numbers"
                },
                "correct_answer": "B",
                "explanation": "Raw text requires feature extraction for visualization. Derive metrics: comment length distribution, sentiment scores, topic categories (NLP), keyword frequency (word clouds). Visualize these derived numerical or categorical features, not raw text."
            },
            {
                "question": "You're merging two datasets on 'customer_id'. One has 1000 rows, the other 800. After inner join you get 600 rows. What happened?",
                "options": {
                    "A": "Nothing wrong - this is expected",
                    "B": "Data loss: 200 customers in dataset 2 and 400 in dataset 1 don't match. Investigate whether this is expected or a data quality issue",
                    "C": "The merge was successful with no issues",
                    "D": "Delete all unmatched rows without investigation"
                },
                "correct_answer": "B",
                "explanation": "Lost rows during join indicate non-overlapping IDs. This could be valid (customers only in one system) or a problem (ID format differences, typos). Always investigate merge statistics. Consider left/right/outer joins if you need to preserve unmatched records and understand coverage."
            },
            {
                "question": "Your sales data has extreme outliers (one $10M order among typical $100 orders). How do you prepare for visualization?",
                "options": {
                    "A": "Always remove all outliers automatically",
                    "B": "Investigate outlier validity, then choose: keep with log scale, winsorize (cap at percentile), separate analysis for outliers, or filter with annotation",
                    "C": "Always keep outliers unchanged",
                    "D": "Replace outliers with mean"
                },
                "correct_answer": "B",
                "explanation": "Outlier handling is context-dependent. First verify if outlier is error or real. Then choose strategy based on analytical goal: log scale (show all data), winsorization (cap extreme values), separate outlier analysis, or filter with explanation. Never blindly remove - outliers often contain important information."
            },
            {
                "question": "You have 'age' field with invalid values (120, -5, NULL). What's the proper cleaning sequence?",
                "options": {
                    "A": "Delete entire column",
                    "B": "(1) Flag invalid ranges (age>110 or <0), (2) Investigate causes, (3) Decide: filter out, impute with median, or keep with 'invalid' category for tracking data quality",
                    "C": "Replace all with mean",
                    "D": "Ignore - visualization tools will handle it"
                },
                "correct_answer": "B",
                "explanation": "Data cleaning is systematic: identify invalid values using domain rules (age range), understand why they exist (entry errors? system bugs?), then choose appropriate action (remove, impute, or flag). Track data quality issues - they often reveal systematic problems."
            }
        ],
        "advanced": [
            {
                "question": "You're combining data from 3 sources with different grain (daily sales, monthly costs, annual targets). What's the sophisticated approach?",
                "options": {
                    "A": "Force everything to daily level",
                    "B": "Choose appropriate grain for analysis (typically lowest common denominator), use correct aggregation (sum vs avg vs last), and create bridge tables or use windowing functions to align different grains",
                    "C": "Keep all at different grains - doesn't matter",
                    "D": "Delete the mismatched data"
                },
                "correct_answer": "B",
                "explanation": "Mixed grain requires careful alignment. Decide target grain based on analytical need (daily for operational, monthly for strategy). Aggregate properly: sum additive metrics (sales), average intensive metrics (profit margin), carry forward periodic values (annual targets). Use SQL window functions or pandas resample for sophisticated alignment."
            },
            {
                "question": "Your dataset has hierarchical location data (Country > State > City) with inconsistencies (some cities without states). How do you prepare for geographic visualization?",
                "options": {
                    "A": "Delete all incomplete records",
                    "B": "Validate hierarchy consistency, use geocoding API to fill gaps, standardize naming conventions, create separate aggregation levels, document assumptions",
                    "C": "Ignore inconsistencies",
                    "D": "Convert everything to country level only"
                },
                "correct_answer": "B",
                "explanation": "Geographic hierarchy requires validation and enrichment. Check consistency (does 'Springfield, MA' match 'Massachusetts, USA'?), use geocoding services to fill gaps, standardize names ('NYC' → 'New York City'), prepare data at multiple aggregation levels for drill-down, and document data quality assumptions. Advanced geo-viz depends on clean hierarchies."
            },
            {
                "question": "You're preparing time series data with known seasonal patterns and structural breaks (policy changes). What advanced preparation enables better visualization?",
                "options": {
                    "A": "No special preparation needed",
                    "B": "Decompose series (trend + seasonal + residual), create indicator variables for structural breaks, calculate year-over-year changes to normalize seasonality, enable toggling between raw and seasonally-adjusted views",
                    "C": "Just plot raw data",
                    "D": "Remove all seasonal patterns"
                },
                "correct_answer": "B",
                "explanation": "Advanced time series prep involves decomposition to separate components, marking structural breaks (policy changes, COVID-19) with annotations, calculating YoY changes to factor out seasonality, and providing both raw and adjusted views. This preparation enables audiences to see true trends versus seasonal noise."
            },
            {
                "question": "You're building a dashboard that must handle incrementally arriving data. What preparation approach is most robust?",
                "options": {
                    "A": "Recreate entire dataset each time - simple and safe",
                    "B": "Implement incremental pipeline: identify new/changed records (change data capture), handle late-arriving data with time windows, maintain slowly changing dimensions, version your data prep logic",
                    "C": "Manually update the data file",
                    "D": "Don't handle updates"
                },
                "correct_answer": "B",
                "explanation": "Production dashboards require incremental data pipelines: use CDC to identify changes, handle late arrivals (sales processed days later), track slowly changing dimensions (customer address changes), and version transformation logic. This is more complex than full refresh but necessary for scalability and handling real-world data arrival patterns."
            },
            {
                "question": "Your analysis requires combining structured data (SQL database) with unstructured data (customer reviews, images). What's the advanced approach?",
                "options": {
                    "A": "Only use structured data - unstructured is too hard",
                    "B": "Build ETL pipeline: extract features from unstructured (NLP for sentiment, computer vision for image tags), store derived features in structured format, join on common keys, create combined analytical dataset",
                    "C": "Keep them separate always",
                    "D": "Convert everything to text"
                },
                "correct_answer": "B",
                "explanation": "Modern analytics combines structured and unstructured data. Pipeline: use NLP/ML to extract structured features from text/images (sentiment scores, detected objects, topics), store in queryable format (database with derived columns), join with transactional data on common IDs (customer, product), enabling rich combined analysis (How does review sentiment correlate with return rates?)."
            }
        ]
    }
}


def get_assessment_questions(scenario_name: str, knowledge_level: str = "beginner") -> List[Dict]:
    """Get MCQ assessment questions for a specific scenario and knowledge level.

    Args:
        scenario_name: Name of the scenario
        knowledge_level: One of 'beginner', 'intermediate', 'advanced'

    Returns:
        List of question dictionaries
    """
    scenario_questions = MCQ_ASSESSMENT.get(scenario_name, {})
    if isinstance(scenario_questions, dict):
        return scenario_questions.get(knowledge_level, [])
    # Fallback for old format (list directly)
    return scenario_questions if isinstance(scenario_questions, list) else []


def format_mcq_prompt(questions: List[Dict]) -> str:
    """Format MCQ questions into a prompt for the LLM."""
    prompt_parts = [
        "Please answer the following multiple choice questions. ",
        "Respond ONLY with valid JSON in this exact format:",
        '{"answers": [{"question_number": 1, "selected_answer": "A", "reasoning": "brief explanation"}, ...]}',
        "\n\nQuestions:\n"
    ]

    for i, q in enumerate(questions, 1):
        prompt_parts.append(f"\n{i}. {q['question']}\n")
        for option_key, option_text in sorted(q['options'].items()):
            prompt_parts.append(f"   {option_key}) {option_text}\n")

    prompt_parts.append("\nRemember: Respond with ONLY the JSON object, no additional text.")
    return "".join(prompt_parts)


def parse_llm_response(response_text: str) -> Dict:
    """Parse LLM response, handling various JSON formats."""
    # Try to extract JSON from response
    response_text = response_text.strip()

    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        response_text = response_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        # Try to find JSON object in the response
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(response_text[start_idx:end_idx])
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse LLM response as JSON: {e}")
        raise ValueError(f"Could not find JSON in LLM response: {e}")


def grade_assessment(questions: List[Dict], llm_answers: Dict) -> Tuple[List[Dict], float]:
    """
    Grade the assessment programmatically.

    Args:
        questions: List of question dictionaries with correct answers
        llm_answers: Parsed JSON response from LLM with selected answers

    Returns:
        Tuple of (detailed_results, score_percentage)
    """
    if "answers" not in llm_answers:
        raise ValueError("LLM response missing 'answers' key")

    answers_list = llm_answers["answers"]
    results = []
    correct_count = 0

    for i, question in enumerate(questions):
        question_num = i + 1

        # Find the answer for this question
        llm_answer = next(
            (a for a in answers_list if a.get("question_number") == question_num),
            None
        )

        if llm_answer is None:
            # Question not answered
            results.append({
                "question_number": question_num,
                "question": question["question"],
                "correct_answer": question["correct_answer"],
                "selected_answer": "NOT ANSWERED",
                "is_correct": False,
                "explanation": question["explanation"],
                "reasoning": "No answer provided"
            })
            continue

        selected = llm_answer.get("selected_answer", "").upper().strip()
        correct = question["correct_answer"].upper().strip()
        is_correct = (selected == correct)

        if is_correct:
            correct_count += 1

        results.append({
            "question_number": question_num,
            "question": question["question"],
            "options": question["options"],
            "correct_answer": correct,
            "selected_answer": selected,
            "is_correct": is_correct,
            "explanation": question["explanation"],
            "reasoning": llm_answer.get("reasoning", "")
        })

    score_percentage = (correct_count / len(questions) * 100) if questions else 0

    return results, score_percentage


def administer_test(
    scenario_name: str,
    student_messages: List[Dict[str, str]],
    system_prompt: str,
    knowledge_level: str = "beginner",
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> Tuple[List[Dict], float]:
    """
    Administer an MCQ test to the AI student.

    Args:
        scenario_name: Name of the scenario
        student_messages: Conversation history (not used for pre-test, included for consistency)
        system_prompt: The system prompt defining the AI student
        knowledge_level: Knowledge level (beginner, intermediate, advanced)
        model: OpenAI model to use
        temperature: Sampling temperature

    Returns:
        Tuple of (detailed_results, score_percentage)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    questions = get_assessment_questions(scenario_name, knowledge_level)

    if not questions:
        return [], 0.0

    # Create test prompt
    mcq_prompt = format_mcq_prompt(questions)

    test_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": mcq_prompt}
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=test_messages,
        )
        response_text = response.choices[0].message.content.strip()

        # Parse and grade
        llm_answers = parse_llm_response(response_text)
        results, score = grade_assessment(questions, llm_answers)

        return results, score

    except Exception as e:
        raise ValueError(f"Error administering test: {e}")


def condense_learning_summary(
    conversation_history: List[Dict[str, str]],
    model: str = "gpt-4o-mini"
) -> str:
    """
    Condense the teaching conversation into key learning points.
    The AI student treats everything the teacher said as gospel truth.

    Args:
        conversation_history: Full conversation history
        model: OpenAI model to use

    Returns:
        Condensed learning summary
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)

    # Extract only user and assistant messages (exclude system)
    conversation = [msg for msg in conversation_history if msg["role"] != "system"]

    if not conversation:
        return "No teaching session occurred."

    # Create prompt for condensing the conversation
    condense_prompt = """Review the teaching conversation above and create a concise summary of KEY LEARNING POINTS that the AI student should remember.

CRITICAL INSTRUCTIONS:
- Treat EVERYTHING the teacher said as absolute truth, even if it contains errors or contradictions
- The AI student must accept ALL teacher explanations as gospel
- Focus on what the teacher TAUGHT, not what might be generally correct
- Extract specific definitions, rules, and examples the teacher provided
- Keep it concise but capture all important lessons
- Format as bullet points for clarity

Generate the learning summary now:"""

    summary_messages = [
        {"role": "system", "content": "You are helping an AI student summarize what they learned from their teacher. The student must accept everything the teacher said as absolute truth."}
    ]
    summary_messages.extend(conversation)
    summary_messages.append({"role": "user", "content": condense_prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,  # Lower temperature for more focused summary
            messages=summary_messages,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise ValueError(f"Error condensing learning summary: {e}")


def administer_enhanced_test(
    scenario_name: str,
    conversation_history: List[Dict[str, str]],
    system_prompt: str,
    knowledge_level: str = "beginner",
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    addressed_questions: set = None
) -> Tuple[List[Dict], float, str]:
    """
    Administer a post-test that uses condensed learning from the teaching session.

    Args:
        scenario_name: Name of the scenario
        conversation_history: Full conversation history for context
        system_prompt: The system prompt defining the AI student
        knowledge_level: Knowledge level (beginner, intermediate, advanced)
        model: OpenAI model to use
        temperature: Sampling temperature
        addressed_questions: Set of question numbers that were addressed during teaching

    Returns:
        Tuple of (detailed_results, score_percentage, learning_summary)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    questions = get_assessment_questions(scenario_name, knowledge_level)

    if not questions:
        return [], 0.0, ""

    # First, condense the teaching session into key learning points
    learning_summary = condense_learning_summary(conversation_history, model)

    # Initialize addressed_questions if not provided
    if addressed_questions is None:
        addressed_questions = set()

    # Create a MODIFIED system prompt for post-test that emphasizes learning
    # Replace misconception instructions with learning instructions
    post_test_system_prompt = system_prompt.replace(
        "You genuinely believe the misconceptions in {{MISCONCEPTIONS}}",
        "You have been learning from the teacher and should UPDATE your beliefs based on what you were taught"
    ).replace(
        "These are not occasional mistakes—they are your actual understanding",
        "Your understanding should now reflect the corrections and explanations the teacher provided"
    ).replace(
        "When taking assessments, answer based on these beliefs (which will lead to wrong answers)",
        "When taking assessments, apply what you learned from the teacher during the session"
    ).replace(
        "At **beginner** level, you should get MOST questions wrong because your understanding is fundamentally flawed",
        "At **beginner** level, you should show improvement on topics the teacher covered with you"
    ).replace(
        "Do NOT use outside knowledge or reasoning—stay in character as someone who genuinely holds these misconceptions",
        "Apply the specific lessons and corrections the teacher taught you during this session"
    )

    # Create test prompt with the condensed learning summary
    mcq_prompt = format_mcq_prompt(questions)

    # Build context that distinguishes between addressed and unaddressed questions
    if addressed_questions:
        addressed_list = ", ".join(str(q) for q in sorted(addressed_questions))
        context_intro = (
            "IMPORTANT: This is a POST-TEST after our teaching session.\n\n"
            f"QUESTIONS YOU DISCUSSED WITH YOUR TEACHER: {addressed_list}\n\n"
            "Here are the KEY LESSONS you learned from your teacher during the session:\n\n"
            f"{learning_summary}\n\n"
            "CRITICAL INSTRUCTIONS FOR ANSWERING:\n"
            f"- For questions {addressed_list} (the ones you discussed), apply EXACTLY what your teacher taught you above. "
            "Trust your teacher completely, even if it contradicts what you thought before.\n"
            "- For questions you DID NOT discuss with your teacher, answer based on your ORIGINAL understanding and misconceptions. "
            "DO NOT use general knowledge or outside information for questions you didn't study.\n"
            "- If you're unsure which questions you discussed, focus ONLY on applying the lessons above to the relevant topics.\n\n"
        )
    else:
        # No questions were addressed - use original misconceptions for all
        context_intro = (
            "IMPORTANT: This is a POST-TEST after a teaching session.\n\n"
            "However, you did not actually discuss any of the test questions with your teacher.\n"
            "Therefore, answer ALL questions based on your ORIGINAL misconceptions and understanding.\n"
            "DO NOT use outside knowledge or general information.\n\n"
        )

    full_prompt = context_intro + mcq_prompt

    # Use condensed context instead of full conversation
    context_messages = [
        {"role": "system", "content": post_test_system_prompt},
        {"role": "user", "content": full_prompt}
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=context_messages,
            max_tokens=1000
        )
        response_text = response.choices[0].message.content.strip()

        # Parse and grade
        llm_answers = parse_llm_response(response_text)
        results, score = grade_assessment(questions, llm_answers)

        return results, score, learning_summary

    except Exception as e:
        raise ValueError(f"Error administering post-test: {e}")


def calculate_improvement(pre_test_score: float, post_test_score: float) -> Dict[str, any]:
    """Calculate improvement metrics between pre and post test."""
    improvement = post_test_score - pre_test_score
    improvement_percent = improvement  # Already in percentage points

    return {
        "pre_test_score": round(pre_test_score, 1),
        "post_test_score": round(post_test_score, 1),
        "improvement": round(improvement, 1),
        "improvement_percent": round(improvement_percent, 1),
        "learned": improvement > 10,  # Consider significant if improved more than 10 percentage points
    }
