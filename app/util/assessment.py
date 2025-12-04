"""Assessment module for generating and evaluating pre/post tests for AI tutee.

Uses multiple choice questions (MCQ) that can be programmatically graded.
Each level has questions specifically designed to be failed by someone holding that level's misconceptions.

Key design principles:
- BEGINNER: Questions trap surface-level reasoning (looks like a number = is a number)
- INTERMEDIATE: Questions trap partial knowledge (knows the rule, misapplies it)
- ADVANCED: Questions trap overgeneralization (applies rule too rigidly, misses context)
"""

from typing import Dict, List, Tuple, Optional
import os
import json
from openai import OpenAI


# =============================================================================
# DATA TYPES SCENARIO
# =============================================================================

DATA_TYPES_BEGINNER = [
    {
        "question": "A dataset has a column 'ProductID' with values like 1001, 1002, 1003. What type of data is this?",
        "options": {
            "A": "Numerical data - we can calculate the average ProductID",
            "B": "Numerical data - we can do math with these numbers",
            "C": "Categorical data - these are just labels for products",
            "D": "Continuous data - IDs can be any number"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["treat_ids_as_numeric_values"],
        "explanation": "ProductID is categorical (nominal) data. Even though it uses numbers, these are just labels - calculating 'average ProductID' is meaningless."
    },
    {
        "question": "Survey responses are coded as: 1='Very Unhappy', 2='Unhappy', 3='Neutral', 4='Happy', 5='Very Happy'. What type of data is this?",
        "options": {
            "A": "This is numerical data",
            "B": "These are categories with words, not real numbers",
            "C": "This is ordinal data",
            "D": "This is none of the above"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["assume_ordinal_behaves_like_continuous"],
        "explanation": "This is ordinal data - the data is categorical but also has an order and can be encoded as a number. However, you can't do full math on it like true numerical data."
    },
    {
        "question": "Which of these is TRUE numerical data that you can do math with?",
        "options": {
            "A": "Phone numbers (555-1234)",
            "B": "Student ID numbers (20240001)",
            "C": "Temperature in Fahrenheit (72.5°F)",
            "D": "ZIP codes (90210)"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["treat_ids_as_numeric_values"],
        "explanation": "Only temperature is truly numerical - you can meaningfully add, subtract, or average temperatures. The others use numbers as labels."
    },
    {
        "question": "A column 'OrderNumber' has values 1, 2, 3, 4, 5 representing the sequence customers placed orders. What type of data is this?",
        "options": {
            "A": "Numerical and Continuous",
            "B": "Numerical and Discrete",
            "C": "Categorical",
            "D": "Ordinal"
        },
        "correct_answer": "D",
        "trap_answer": "A",
        "triggered_by": ["treat_ids_as_numeric_values", "assume_ordinal_behaves_like_continuous"],
        "explanation": "Order sequence is ordinal - 2nd comes after 1st, but 'Order 4 minus Order 2 equals Order 2' makes no sense."
    },
    {
        "question": "You have employee ages: 25, 32, 28, 45, 38. What can you do with this data?",
        "options": {
            "A": "Nothing - ages are just labels for people",
            "B": "Calculate average age, find the range, compare who is older",
            "C": "Only count how many people are in each age",
            "D": "Ages should be converted to categories like 'young' and 'old' first"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["treat_ids_as_numeric_values"],
        "explanation": "Age is true numerical (ratio) data - you can meaningfully calculate averages, differences, and comparisons. This is NOT like ID numbers."
    }
]

DATA_TYPES_INTERMEDIATE = [
    {
        "question": "You want to create a scatterplot showing customer age vs. monthly spending. Your dataset contains both 'CustomerAge' (25, 32, 45) and 'AgeGroup' ('18–30', '31–50', '51+'). Which should you use on the x-axis and why?",
        "options": {
            "A": "AgeGroup, because categories are easier to read than numbers",
            "B": "CustomerAge, because it preserves precise continuous variation and prevents artificial vertical banding",
            "C": "Either one, because they contain the same information",
            "D": "AgeGroup, because regression works better on categories"
        },
        "correct_answer": "B",
        "trap_answer": "C",
        "triggered_by": ["ignore_context_in_continuous_to_categorical_conversion"],
        "explanation": "Using AgeGroup introduces visual binning that hides within-group variation and creates artificial stripes. Continuous axes preserve patterns like nonlinearity and heteroscedasticity."
    },
    {
        "question": "You're analyzing US data with ZIP codes (10001, 90210, 60601). What type of data is the ZIP code field?",
        "options": {
            "A": "Continuous numerical data",
            "B": "Discrete numerical data",
            "C": "Categorical (nominal) identifier data",
            "D": "Ordinal data, because some ZIP codes are larger than others"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["confuse_zip_codes_as_numerical"],
        "explanation": "ZIP codes are identifiers, not measurements. Their numeric values and ordering have no quantitative meaning, so they must be treated as nominal categorical data."
    },
    {
        "question": "A 'Satisfaction' column has values 1-10 from a survey. Your analyst treats it as continuous and calculates mean=7.3. Your manager says it's ordinal and wants the median. Who's right?",
        "options": {
            "A": "The analyst - any numbers can be averaged",
            "B": "The manager - survey responses are always ordinal",
            "C": "Both have valid points - for 1-10 scales, mean is often acceptable but median is more robust; report both",
            "D": "Neither - you should convert to categories first"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["treat_rating_scales_inconsistently"],
        "explanation": "This is a judgment call. Wide scales (1-10) are often treated as approximately continuous, but technically they're ordinal. Best practice: report both mean and median, acknowledge the assumption."
    },
    {
        "question": "A revenue column contains values like '$1,234', '$5,678', '$999'. Before choosing a chart, how should this field be classified?",
        "options": {
            "A": "Categorical data because it contains symbols",
            "B": "Ordinal data because the values have an order",
            "C": "Continuous data stored as text",
            "D": "Dollar data because it contains dollar signs"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["mishandle_mixed_unit_data", "confuse_numerical_encoding_with_numeric_measurement"],
        "explanation": "Revenue is numerical data (true zero, meaningful ratios), but it is currently stored as text due to formatting. The data type does not change just because the storage type is string."
    },
    {
        "question": "You have an 'EmployeeRank' field where 1=Junior, 2=Mid, 3=Senior, 4=Lead, 5=Director. How should this field be classified before choosing a chart?",
        "options": {
            "A": "Numerical ratio data",
            "B": "Numerical interval data",
            "C": "Categorical ordinal data",
            "D": "Categorical nominal data"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["treat_rating_scales_inconsistently"],
        "explanation": "EmployeeRank represents ordered categories. While it is encoded with numbers, the spacing between ranks is not guaranteed to be equal, so it is ordinal—not interval or ratio."
    }
]

DATA_TYPES_ADVANCED = [
    {
        "question": "An analyst argues that because income is highly skewed (mean=$85K, median=$52K), it should no longer be treated as quantitative data for visualization. Why is this reasoning flawed?",
        "options": {
            "A": "Skew does not change the fact that income is ratio-scale numerical data",
            "B": "Skewed data must always be binned into categories",
            "C": "Skew means the data becomes ordinal instead of numerical",
            "D": "Skew means only medians are allowed, not values"
        },
        "correct_answer": "A",
        "trap_answer": "C",
        "triggered_by": ["miss_ratio_vs_interval_scale_distinctions", "overlook_distribution_impact_on_type_choice"],
        "explanation": "Distribution shape affects how we summarize or scale data, not the underlying measurement level. Income remains ratio-scale numerical regardless of skew."
    },
    {
        "question": "You observe response times where 99% fall between 50–200ms, but 1% are 5000–30000ms (timeouts). What does this imply about the underlying data type?",
        "options": {
            "A": "It is a single continuous ratio variable with extreme values",
            "B": "It is ordinal data because the values are ordered by speed",
            "C": "It reflects a mixture of two different variable types: continuous response time and a separate binary timeout event",
            "D": "It becomes categorical because of the extreme separation"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["overlook_distribution_impact_on_type_choice"],
        "explanation": "The extreme separation suggests two distinct processes: real-valued continuous response time and a discrete timeout event. Treating this as one continuous variable hides an important structural distinction in the data."
    },
    {
        "question": "A 'Priority' field uses P0, P1, P2, P3 where P0=Critical and P3=Low. After encoding it as 0,1,2,3, which incorrect assumption might this introduce about the data type?",
        "options": {
            "A": "That it is still purely nominal data",
            "B": "That the differences between levels are equal, as if it were interval-scale",
            "C": "That the values now represent true ratios of urgency",
            "D": "That the field can no longer be sorted"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["miss_ratio_vs_interval_scale_distinctions"],
        "explanation": "Priority is ordinal by nature. Encoding as 0,1,2,3 can mistakenly suggest equal spacing between levels (interval scale), even if business impact differs dramatically between P0 and P1."
    },
    {
        "question": "Age is a ratio-scale continuous variable. When you bin it into ranges like '18–25', '26–35', what does the variable become?",
        "options": {
            "A": "Nominal categorical data",
            "B": "Ordinal categorical data",
            "C": "Interval numerical data",
            "D": "Binary categorical data"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["ignore_context_in_continuous_to_categorical_conversion"],
        "explanation": "Binning a continuous ratio-scale variable produces an ordinal categorical variable: categories with a meaningful order but no precise numerical distances."
    },
    {
        "question": "A paper reports a 'mean temperature increase of 2.3°C' and discusses percentage changes. Why is this a data type issue?",
        "options": {
            "A": "Because Celsius is noisy but Kelvin is more precise",
            "B": "Because Celsius is an interval scale and does not support ratio or percentage claims",
            "C": "Because all physical measurements are automatically ratio scale",
            "D": "Because averages cannot be computed on temperature data"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["miss_ratio_vs_interval_scale_distinctions"],
        "explanation": "Celsius is interval scale: zero is arbitrary. This means ratio statements (e.g., 'twice as hot') and percent changes are invalid unless the data is converted to an absolute scale like Kelvin (ratio)."
    }
]


# =============================================================================
# TYPE TO CHART SCENARIO
# =============================================================================

TYPE_TO_CHART_BEGINNER = [
    {
        "question": "You have sales data for 5 product categories (Electronics, Clothing, Food, Books, Toys). Which chart should you use to compare their sales?",
        "options": {
            "A": "Line chart connecting the categories",
            "B": "Bar chart with one bar per category",
            "C": "Scatter plot of categories vs sales",
            "D": "Line chart because sales are numbers"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["use_line_for_categories"],
        "explanation": "Bar charts are for comparing categories. Line charts imply a continuous connection between points - there's no meaningful 'between' Electronics and Clothing."
    },
    {
        "question": "You want to show how website traffic changed over 12 months. Which chart is best?",
        "options": {
            "A": "Pie chart with 12 slices (one per month)",
            "B": "Bar chart with 12 bars",
            "C": "Line chart showing the trend over time",
            "D": "Scatter plot of month vs traffic"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["default_to_pie_with_many_categories"],
        "explanation": "Line charts show trends over time - the connection between points is meaningful. Pie charts show parts of a whole, not time trends. A pie with 12 slices would be hard to read and wouldn't show the trend."
    },
    {
        "question": "You need to show what percentage of total revenue comes from each of 4 regions. Which chart is most appropriate?",
        "options": {
            "A": "Line chart",
            "B": "Pie chart or 100% stacked bar",
            "C": "Scatter plot",
            "D": "Histogram"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["use_line_for_categories"],
        "explanation": "Parts of a whole (composition) = pie chart or 100% stacked bar. Line charts are for trends over continuous dimensions, not composition."
    },
    {
        "question": "You have customer satisfaction scores (1-5) for 3 store locations. Which chart shows this comparison clearly?",
        "options": {
            "A": "Line chart connecting the 3 stores",
            "B": "Pie chart showing score distribution",
            "C": "Bar chart with one bar per store showing average score",
            "D": "Line chart because scores are numbers"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["use_line_for_categories"],
        "explanation": "Comparing values across categories (stores) = bar chart. Line charts suggest Store A leads to Store B which is meaningless - stores aren't ordered or connected."
    },
    {
        "question": "Your manager wants to show sales for 15 different products using a pie chart. What's the problem?",
        "options": {
            "A": "Nothing - pie charts work for any number of categories",
            "B": "15 slices are too many - pie charts work best with 3-7 categories; use a bar chart instead",
            "C": "Pie charts can't show sales data",
            "D": "You need a 3D pie chart for this many categories"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["default_to_pie_with_many_categories"],
        "explanation": "Pie charts become unreadable with many slices. Humans can't easily compare 15 slice angles. Use a bar chart (sorted by value) for many categories."
    }
]

TYPE_TO_CHART_INTERMEDIATE = [
    {
        "question": "You need to show sales trends for 4 regions over 12 months. Which approach is best?",
        "options": {
            "A": "4 separate pie charts (one per region)",
            "B": "Single line chart with 4 lines (one per region)",
            "C": "48 individual bars (4 regions × 12 months)",
            "D": "4 separate scatter plots"
        },
        "correct_answer": "B",
        "trap_answer": "C",
        "triggered_by": ["fail_to_consider_category_count", "overlook_dual_dimension_chart_options"],
        "explanation": "Multiple lines on one chart efficiently show trends AND allow comparison between regions. 48 bars would be overwhelming; pie charts can't show trends."
    },
    {
        "question": "You have 500 data points with X (age) and Y (income). You want to see if there's a relationship. Best chart?",
        "options": {
            "A": "Bar chart of average income per age",
            "B": "Line chart connecting age to income",
            "C": "Scatter plot showing all 500 points",
            "D": "Pie chart of income distribution"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["overlook_dual_dimension_chart_options"],
        "explanation": "Scatter plots show relationships between two numerical variables. You can see correlations, clusters, and outliers. A line chart implies ordered connection; bar chart loses individual data points."
    },
    {
        "question": "Your data has 50 product categories. You need to compare their sales. What's the best approach?",
        "options": {
            "A": "Bar chart with 50 bars",
            "B": "Pie chart with 50 slices",
            "C": "Show top 10 in a bar chart, group the rest as 'Other', or use a treemap",
            "D": "Line chart connecting all 50 products"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["fail_to_consider_category_count"],
        "explanation": "50 bars is too many to compare effectively. Better: focus on top performers, aggregate the long tail, or use a treemap which handles many categories well."
    },
    {
        "question": "You have hourly temperature readings for a full year (8,760 data points). Best visualization?",
        "options": {
            "A": "Bar chart with 8,760 bars",
            "B": "Line chart showing all hourly points",
            "C": "Aggregate to daily or weekly, then show as line chart; or use a heatmap (hour × day)",
            "D": "Pie chart of temperature ranges"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["ignore_data_granularity_effects"],
        "explanation": "8,760 points on a line chart creates visual noise. Better: aggregate to appropriate granularity (daily for trends, weekly for patterns) or use a heatmap to show hour-of-day patterns across months."
    },
    {
        "question": "You want to show how 3 metrics (Revenue, Costs, Profit) changed over 12 months. Best approach?",
        "options": {
            "A": "3 separate charts, one per metric",
            "B": "One line chart with 3 lines (different colors)",
            "C": "Stacked bar chart",
            "D": "Either A or B depending on whether comparison across metrics or trend within each metric is more important"
        },
        "correct_answer": "D",
        "trap_answer": "B",
        "triggered_by": ["overlook_dual_dimension_chart_options"],
        "explanation": "It depends on the goal. If comparing metrics to each other matters, use one chart with 3 lines. If each metric's trend is primary, separate charts (same scale) work. Context determines the best choice."
    }
]

TYPE_TO_CHART_ADVANCED = [
    {
        "question": "You need to visualize 4 dimensions: Time, Region (5 values), Product (10 values), and Revenue. What's the best approach?",
        "options": {
            "A": "A single 3D chart encoding all dimensions",
            "B": "Small multiples: 5 line charts (one per region), each showing Product × Time × Revenue, or an interactive dashboard with filters",
            "C": "One line chart with 50 lines (5 regions × 10 products)",
            "D": "Just pick the 2 most important dimensions"
        },
        "correct_answer": "B",
        "trap_answer": "C",
        "triggered_by": ["create_overly_complex_single_charts"],
        "explanation": "50 lines is unreadable. High-dimensional data requires smart decomposition: small multiples, faceting, or interactive filters. A single complex chart fails; arbitrarily dropping dimensions loses insight."
    },
    {
        "question": "You want to show a bimodal distribution (two peaks: quick responses ~50ms, timeout responses ~5000ms). Best visualization?",
        "options": {
            "A": "Simple histogram with auto-binning",
            "B": "Box plot showing median and quartiles",
            "C": "Histogram with log-scale x-axis, or two separate histograms for each mode, or violin plot",
            "D": "Just report the mean and standard deviation"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["choose_specialized_chart_types"],
        "explanation": "Auto-binned histogram will likely hide the bimodality (one peak dominates). Log scale reveals both modes; separated histograms make the two processes explicit; violin plots show the full distribution shape."
    },
    {
        "question": "You're building a real-time dashboard showing stock prices updating every second. What's the critical design consideration?",
        "options": {
            "A": "Use the most visually appealing chart type",
            "B": "Show all historical data to provide complete context",
            "C": "Implement a sliding time window and appropriate aggregation to balance real-time updates with context and prevent visual overload",
            "D": "Update the y-axis scale with each new data point"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["ignore_streaming_data_constraints"],
        "explanation": "Showing all history creates ever-growing, slow, cluttered charts. Constantly rescaling y-axis makes trends impossible to track. Sliding windows (last N minutes) with smart aggregation balance recency and context."
    },
    {
        "question": "Your dataset shows company hierarchy: Company → Division → Department → Team. You want to show headcount at each level. Best chart?",
        "options": {
            "A": "Bar chart with all units on x-axis",
            "B": "Treemap (nested rectangles) or sunburst chart that encodes the hierarchy",
            "C": "Pie chart of headcount",
            "D": "Scatter plot"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["handle_high_dimensional_data"],
        "explanation": "Hierarchical data needs hierarchical visualization. Treemaps show size AND structure (which teams are in which departments). Flat bar charts lose the hierarchy entirely."
    },
    {
        "question": "You have highly skewed data (power law: few very large values, many small). You want to show the overall pattern AND let users see details. Best approach?",
        "options": {
            "A": "Single linear-scale chart (shows true values)",
            "B": "Single log-scale chart (compresses range)",
            "C": "Coordinated views: log-scale for overview + linear-scale detail view with filter/zoom, or interactive chart with scale toggle",
            "D": "Remove outliers to make a normal-looking distribution"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["underuse_coordinated_views"],
        "explanation": "Single log scale reveals pattern but obscures small values. Single linear scale shows detail but compresses most data. Coordinated views (or interactive scale toggle) provide both overview and detail. Never remove outliers from power law data - they ARE the pattern."
    }
]


# =============================================================================
# CHART TO TASK SCENARIO  
# =============================================================================

CHART_TO_TASK_BEGINNER = [
    {
        "question": "Your task is: 'Show how our sales have grown over the past year.' Which chart matches this task?",
        "options": {
            "A": "Pie chart showing this year's sales breakdown",
            "B": "Bar chart comparing sales of different products",
            "C": "Line chart showing sales by month",
            "D": "Scatter plot of sales vs expenses"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["confuse_rank_with_trend", "assume_one_chart_fits_all_tasks"],
        "explanation": "The task is about TREND over TIME ('grown over the past year'). Line charts show trends. Pie charts show composition at a single point, not change over time."
    },
    {
        "question": "Your manager asks: 'Which of our 5 stores has the highest customer satisfaction?' What chart answers this?",
        "options": {
            "A": "Line chart showing satisfaction over time",
            "B": "Bar chart comparing satisfaction scores across stores",
            "C": "Pie chart of total customers per store",
            "D": "Scatter plot"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["confuse_rank_with_trend"],
        "explanation": "The task is COMPARISON ('which store has highest'). Bar charts compare values across categories. Line charts are for trends over time, which isn't what was asked."
    },
    {
        "question": "Task: 'What portion of our revenue comes from each product line?' Which chart type fits?",
        "options": {
            "A": "Line chart",
            "B": "Scatter plot",
            "C": "Pie chart or 100% stacked bar",
            "D": "Histogram"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["assume_one_chart_fits_all_tasks"],
        "explanation": "The task is COMPOSITION ('portion of total'). Pie charts and 100% stacked bars show parts of a whole. Line charts show trends, not composition."
    },
    {
        "question": "Task: 'Understand how test scores are spread across our students.' Best visualization?",
        "options": {
            "A": "Pie chart of score ranges",
            "B": "Line chart of scores",
            "C": "Histogram or box plot showing the distribution",
            "D": "Bar chart of student names"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["ignore_distribution_needs"],
        "explanation": "The task is DISTRIBUTION ('how scores are spread'). Histograms and box plots show distribution shape. Pie charts show composition, not distribution."
    },
    {
        "question": "Task: 'Is there a connection between advertising spend and sales?' Which chart helps answer this?",
        "options": {
            "A": "Pie chart of advertising budget",
            "B": "Line chart of sales over time",
            "C": "Scatter plot of advertising spend vs sales",
            "D": "Bar chart comparing different ads"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["assume_one_chart_fits_all_tasks"],
        "explanation": "The task is CORRELATION ('connection between' two variables). Scatter plots show relationships between two numerical variables. Line charts show trends, not correlations."
    }
]

CHART_TO_TASK_INTERMEDIATE = [
    {
        "question": "Task: 'Identify unusual data points that might indicate fraud.' Which visualization best supports this?",
        "options": {
            "A": "Pie chart of transaction types",
            "B": "Bar chart of transaction counts by day",
            "C": "Scatter plot with statistical boundaries (showing points beyond normal range) or box plot highlighting outliers",
            "D": "Line chart of total transaction value"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["overlook_outlier_identification_needs"],
        "explanation": "Finding 'unusual' points = OUTLIER DETECTION. Scatter plots with boundaries or box plots explicitly highlight outliers. Bar charts and pie charts don't reveal individual outliers."
    },
    {
        "question": "Task: 'Show how customers move through our 5-step checkout process, including where they drop off.' Best visualization?",
        "options": {
            "A": "5 pie charts, one for each step",
            "B": "Line chart showing completion rate",
            "C": "Funnel chart or Sankey diagram showing flow and drop-off at each stage",
            "D": "Bar chart of customers at each step"
        },
        "correct_answer": "C",
        "trap_answer": "D",
        "triggered_by": ["ignore_sequential_flow_visualizations"],
        "explanation": "Sequential flow with drop-off = FUNNEL or SANKEY. These show volume at each stage AND the transitions. Bar charts lose the flow/drop-off pattern; pie charts don't show sequence."
    },
    {
        "question": "Task: 'Compare our actual Q3 sales against the target for each of 8 product lines.' Best approach?",
        "options": {
            "A": "Two separate pie charts (actual vs target)",
            "B": "Grouped bar chart or bullet chart showing actual and target side by side for each product",
            "C": "Line chart connecting actual to target",
            "D": "Scatter plot of actual vs target"
        },
        "correct_answer": "B",
        "trap_answer": "D",
        "triggered_by": ["fail_to_plan_for_drill_down_requirements"],
        "explanation": "Comparing actual vs target per category = BULLET CHART or GROUPED BARS. Scatter plot works for correlation analysis but doesn't show the per-product comparison clearly."
    },
    {
        "question": "Task: 'Let analysts explore our dataset to find patterns we haven't anticipated.' Best approach?",
        "options": {
            "A": "Pre-built dashboard with fixed charts showing known KPIs",
            "B": "Scatter plot matrix (all variable pairs) or interactive tool with filters and multiple coordinated views",
            "C": "Single summary table with all metrics",
            "D": "One comprehensive chart showing all dimensions"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["choose_charts_for_exploratory_analysis"],
        "explanation": "EXPLORATION requires seeing patterns from multiple angles. Scatter plot matrices show all relationships; interactive tools allow hypothesis testing. Fixed dashboards only answer predetermined questions."
    },
    {
        "question": "Task: 'Track our progress toward the annual goal, with context of how we did last year.' Best visualization?",
        "options": {
            "A": "Single number showing percent of goal achieved",
            "B": "Line chart showing current year only",
            "C": "Line chart with current year prominent and last year as reference (gray line or shaded band)",
            "D": "Bar chart comparing this year vs last year totals"
        },
        "correct_answer": "C",
        "trap_answer": "B",
        "triggered_by": ["confuse_rank_with_trend"],
        "explanation": "Progress tracking with historical context needs COMPARISON OVER TIME. Showing both years reveals if you're ahead/behind where you were. Current year only loses the comparison; single number loses the trend."
    }
]

CHART_TO_TASK_ADVANCED = [
    {
        "question": "Executive asks: 'Why did revenue drop in Q3?' What visualization approach best answers this diagnostic question?",
        "options": {
            "A": "Single bar chart showing Q3 vs Q2 revenue",
            "B": "Pie chart breaking down Q3 revenue by segment",
            "C": "Drill-down analysis: trend line for context → decomposition by segment/region → correlation with external factors; multiple coordinated views",
            "D": "Table showing all Q3 metrics"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["design_diagnostic_analysis_workflows"],
        "explanation": "'Why' questions (DIAGNOSTIC) require multi-level analysis: confirm the drop (trend), decompose by dimensions (what segments dropped?), correlate with factors (what changed?). One chart can't answer 'why'."
    },
    {
        "question": "Task: 'Build a visualization that lets stakeholders answer their own questions about the data.' What's essential?",
        "options": {
            "A": "Very detailed static charts covering all possible questions",
            "B": "Interactive dashboard with filters, drill-down, and coordinated views that respond to selections",
            "C": "A comprehensive data table",
            "D": "Multiple static reports for different scenarios"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["fail_to_enable_self_service_exploration"],
        "explanation": "SELF-SERVICE = interactivity. Users can't anticipate all questions, so static charts always fall short. Filters, drill-down, and linked selections let users explore and answer their own questions."
    },
    {
        "question": "Task: 'Present A/B test results to decide if the new design is better.' What must your visualization include?",
        "options": {
            "A": "Just the two conversion rates in a bar chart",
            "B": "Bar chart with error bars (confidence intervals), sample sizes, and statistical test results (p-value or confidence level)",
            "C": "Line chart showing both variants over time",
            "D": "Pie charts comparing the two variants"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["provide_insufficient_statistical_context"],
        "explanation": "A/B decisions require STATISTICAL CONFIDENCE, not just observed differences. Show uncertainty (error bars), sample size (affects reliability), and significance test. Without these, you can't distinguish real effects from noise."
    },
    {
        "question": "Task: 'Identify which factors most strongly predict customer churn.' Best analytical visualization?",
        "options": {
            "A": "Bar chart of churn rate by segment",
            "B": "Pie chart of churned vs retained",
            "C": "Feature importance chart from predictive model + distributions of top factors split by churn status",
            "D": "Line chart of churn over time"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["design_diagnostic_analysis_workflows"],
        "explanation": "Identifying DRIVERS (what causes churn) requires statistical/ML analysis, not just descriptive charts. Feature importance quantifies what matters; conditional distributions show how churned vs retained differ on those factors."
    },
    {
        "question": "You need to present to two audiences: executives (want high-level summary) and analysts (want detailed breakdown). Best approach?",
        "options": {
            "A": "One comprehensive detailed report - executives can skim, analysts can dive deep",
            "B": "Layered approach: executive dashboard (KPIs, key trends) with drill-down capability to detailed analyst views; or separate deliverables for each audience",
            "C": "Two versions of the same charts at different sizes",
            "D": "Only detailed version - executives should see the full picture"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["ignore_multi_audience_requirements"],
        "explanation": "Different audiences have different needs. Executives want quick insights and decisions; analysts want exploration and evidence. Layered design (summary → detail) or separate deliverables serves both. One-size-fits-all satisfies neither."
    }
]


# =============================================================================
# DATA PREPARATION SCENARIO
# =============================================================================

DATA_PREPARATION_BEGINNER = [
    {
        "question": "Your date column has mixed formats: '01/15/2024', '2024-02-20', 'March 3, 2024'. What should you do FIRST before making any charts?",
        "options": {
            "A": "Just make the chart - the software will figure it out",
            "B": "Delete the rows with weird formats",
            "C": "Standardize all dates to a single format (e.g., YYYY-MM-DD)",
            "D": "Convert dates to categories like 'Winter' and 'Spring'"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["plot_before_cleaning"],
        "explanation": "Mixed date formats will cause sorting/plotting errors. Always standardize to a single format first. Software often WON'T figure it out correctly."
    },
    {
        "question": "Your revenue column has 20% missing values. Your colleague suggests replacing all missing values with 0. What's wrong with this?",
        "options": {
            "A": "Nothing - 0 is a good placeholder for missing data",
            "B": "Zero is a real value meaning 'no revenue'. Replacing missing with zero falsely claims those records had zero revenue",
            "C": "You should use -1 instead of 0",
            "D": "Missing values don't affect analysis"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["plot_before_cleaning"],
        "explanation": "Zero means 'no revenue' which is different from 'unknown revenue'. Replacing missing with zero will incorrectly lower your averages and totals."
    },
    {
        "question": "You have 1000 rows of individual transactions. You need a chart showing monthly sales totals. What prep step is needed?",
        "options": {
            "A": "Just plot all 1000 transactions - the chart will summarize",
            "B": "Aggregate: group by month and sum the transaction amounts",
            "C": "Delete transactions to get one per month",
            "D": "Convert amounts to percentages"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["aggregate_metrics_twice"],
        "explanation": "You must aggregate transaction-level data to monthly totals. Most chart tools won't automatically sum by month - you'll get a mess of 1000 points or wrong results."
    },
    {
        "question": "Your salary data has mostly values between $40K-$100K, but one entry shows $5,000,000. Before visualizing, you should:",
        "options": {
            "A": "Ignore it - outliers happen",
            "B": "Delete it - it's obviously wrong",
            "C": "Investigate: Is it a data entry error or a real outlier (like CEO pay)? Then decide how to handle it",
            "D": "Change it to the average salary"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["ignore_outliers_affecting_scale"],
        "explanation": "Don't ignore OR blindly delete. A $5M salary could be real (CEO) or an error (missing decimal). Investigate first, then make an informed decision about how to handle it."
    },
    {
        "question": "Your price column shows: '$1,234', '$5,678', '$999'. You try to calculate the average and get an error. Why?",
        "options": {
            "A": "The prices are too different",
            "B": "The data is stored as text (strings) because of '$' and commas - you need to clean and convert to numbers first",
            "C": "You need more prices to calculate an average",
            "D": "Averages don't work with prices"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["mix_units_without_standardizing"],
        "explanation": "Text like '$1,234' isn't a number - it's a string of characters. You must remove $ and commas, then convert to numeric type before doing any math."
    }
]

DATA_PREPARATION_INTERMEDIATE = [
    {
        "question": "You have daily sales data but some days have no records (store was closed). You want to plot daily sales trend. How should you handle the missing days?",
        "options": {
            "A": "Just plot what you have - gaps will show naturally",
            "B": "Create a complete date sequence and explicitly fill missing days with $0 (if closed = no sales) or mark as 'No Data' (if unknown)",
            "C": "Delete the weeks that have missing days",
            "D": "Interpolate the missing values from surrounding days"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["ignore_missing_temporal_data"],
        "explanation": "Gaps in time series can be misleading. Create complete date range and handle missing days explicitly. If closed=$0 is correct, fill with 0. If truly missing, mark it. Don't just ignore or interpolate without understanding why data is missing."
    },
    {
        "question": "You're joining customer data (1000 rows) with orders (800 rows) on customer_id. The join returns 600 rows. What happened and what should you do?",
        "options": {
            "A": "Success! 600 matching customers found",
            "B": "Investigate: 400 customers have no orders, 200 orders have invalid customer_ids - decide if this is expected or a data quality issue",
            "C": "Use a different join type to get all 1800 rows",
            "D": "The join worked correctly, proceed with analysis"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["fail_to_validate_merge_results"],
        "explanation": "Always validate join results! Lost rows could mean: customers who never ordered (fine), OR broken foreign keys (data quality issue). Understanding WHY determines whether results are valid."
    },
    {
        "question": "Sales data has one $10M order among typical $100-$500 orders. You need to visualize the distribution. Best approach?",
        "options": {
            "A": "Remove the $10M outlier to see the 'real' distribution",
            "B": "Keep as-is - outliers are part of the data",
            "C": "Investigate if it's real, then consider: log scale to show all values, separate view for outliers, or winsorization with annotation",
            "D": "Replace with median"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["mishandle_outliers_without_investigation"],
        "explanation": "Don't blindly remove OR blindly keep. A $10M order could be: enterprise deal (real, important), data entry error (fix it), or aggregation mistake (investigate). Your handling depends on what it is."
    },
    {
        "question": "You have a 'comments' text field with customer feedback. How can you use this in data visualization?",
        "options": {
            "A": "Text can't be visualized - ignore this column",
            "B": "Extract features: sentiment scores, word counts, topic categories, keywords - then visualize those derived metrics",
            "C": "Display comments as labels on charts",
            "D": "Convert each unique comment to a number"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["handle_text_feature_extraction"],
        "explanation": "Text requires feature extraction before visualization. NLP can derive: sentiment (positive/negative), topics, word frequency, comment length. Visualize these derived metrics, not raw text."
    },
    {
        "question": "Your age column has values: 25, 32, -5, 150, NULL, 28. What's the proper data cleaning sequence?",
        "options": {
            "A": "Replace invalid values with the mean age",
            "B": "(1) Define valid range rules (0-120), (2) Flag violations (-5, 150), (3) Investigate causes, (4) Decide: fix, remove, or impute based on cause",
            "C": "Delete all rows with bad data",
            "D": "Just use the data as-is - these edge cases won't affect results"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["plot_before_cleaning"],
        "explanation": "Systematic cleaning: (1) Define what's valid, (2) Find violations, (3) Understand WHY (entry error? system bug?), (4) Choose appropriate fix. Blindly replacing with mean hides data quality issues."
    }
]

DATA_PREPARATION_ADVANCED = [
    {
        "question": "You need to combine: daily sales (transaction level), monthly costs (aggregated), and annual targets (single value per year). How do you prepare this for analysis?",
        "options": {
            "A": "Force everything to daily level by dividing monthly and annual values",
            "B": "Determine target analysis grain, aggregate/distribute appropriately (e.g., sum for sales, daily average for costs, repeat annual targets), document assumptions",
            "C": "Just join on date - the database will handle different granularities",
            "D": "Keep separate analyses for each granularity"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["fail_to_align_different_data_grains"],
        "explanation": "Different grains need thoughtful alignment. Simply dividing monthly→daily assumes uniform distribution (often wrong). Decide the right grain for your question, use appropriate aggregation methods (sum for additive metrics, average for rates), and document assumptions."
    },
    {
        "question": "Geographic data has: 'New York', 'NY', 'New York City', 'NYC', 'Manhattan, NY'. Before mapping, you need to:",
        "options": {
            "A": "Use as-is - mapping tools handle synonyms",
            "B": "Delete non-standard entries",
            "C": "Standardize naming (canonicalize to consistent format), use geocoding API to validate/enrich, define hierarchy (NYC contains Manhattan), document mapping decisions",
            "D": "Convert all to coordinates and ignore names"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["ignore_hierarchical_data_consistency"],
        "explanation": "Geographic data needs standardization: 'NYC' = 'New York City', hierarchy matters (Manhattan is part of NYC), geocoding validates locations. Mapping tools usually DON'T handle synonyms well - you'll get split data."
    },
    {
        "question": "Your time series has known seasonality (holiday spikes) and a structural break (COVID-19 impact). How do you prepare for visualization?",
        "options": {
            "A": "Plot raw data - seasonality and breaks are just part of the pattern",
            "B": "Remove seasonality to show 'true' trend",
            "C": "Decompose into components (trend + seasonal + residual), mark structural breaks with annotations, offer both raw and seasonally-adjusted views, calculate YoY changes",
            "D": "Only show data from after the structural break"
        },
        "correct_answer": "C",
        "trap_answer": "A",
        "triggered_by": ["align_multi_grain_data_sources"],
        "explanation": "Advanced time series prep provides multiple views: raw (what happened), seasonally adjusted (underlying trend), YoY changes (normalized comparison), with structural breaks annotated. This enables audiences to understand both what happened and why."
    },
    {
        "question": "You're building a production dashboard that updates with new data daily. What preparation approach is most robust?",
        "options": {
            "A": "Full refresh: recreate all data processing from scratch each day",
            "B": "Incremental pipeline: process only new/changed records, handle late-arriving data with restatement windows, version transformation logic, validate row counts and totals",
            "C": "Manual update when someone notices issues",
            "D": "Cache everything and update monthly"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["overlook_incremental_update_complexity"],
        "explanation": "Full refresh is simple but doesn't scale and can't handle late-arriving data (transactions posted days later). Production systems need: incremental processing, restatement for late data, validation checks, and versioned logic for reproducibility."
    },
    {
        "question": "You need to analyze survey responses (structured) combined with interview transcripts (unstructured). Best data preparation approach?",
        "options": {
            "A": "Keep them completely separate - can't mix structured and unstructured",
            "B": "Build extraction pipeline: derive structured features from transcripts (sentiment, topics, key themes, mentioned entities) via NLP, store as new columns, join with survey responses on participant ID",
            "C": "Manually read transcripts and add notes to spreadsheet",
            "D": "Convert survey responses to text format"
        },
        "correct_answer": "B",
        "trap_answer": "A",
        "triggered_by": ["build_incremental_data_pipelines"],
        "explanation": "Modern analysis integrates structured and unstructured data. Use NLP to extract structured features from text (sentiment scores, topics, entities), then join with structured data on common keys. This enables questions like 'Do interview themes correlate with survey satisfaction?'"
    }
]


# =============================================================================
# COMBINE ALL ASSESSMENTS
# =============================================================================

MCQ_ASSESSMENT = {
    "data_types": {
        "beginner": DATA_TYPES_BEGINNER,
        "intermediate": DATA_TYPES_INTERMEDIATE,
        "advanced": DATA_TYPES_ADVANCED
    },
    "type_to_chart": {
        "beginner": TYPE_TO_CHART_BEGINNER,
        "intermediate": TYPE_TO_CHART_INTERMEDIATE,
        "advanced": TYPE_TO_CHART_ADVANCED
    },
    "chart_to_task": {
        "beginner": CHART_TO_TASK_BEGINNER,
        "intermediate": CHART_TO_TASK_INTERMEDIATE,
        "advanced": CHART_TO_TASK_ADVANCED
    },
    "data_preparation": {
        "beginner": DATA_PREPARATION_BEGINNER,
        "intermediate": DATA_PREPARATION_INTERMEDIATE,
        "advanced": DATA_PREPARATION_ADVANCED
    }
}


# =============================================================================
# ASSESSMENT FUNCTIONS
# =============================================================================

def get_assessment_questions(scenario_name: str, knowledge_level: str = "beginner") -> List[Dict]:
    """Get MCQ assessment questions for a specific scenario and knowledge level."""
    scenario_questions = MCQ_ASSESSMENT.get(scenario_name, {})
    if isinstance(scenario_questions, dict):
        return scenario_questions.get(knowledge_level, [])
    return scenario_questions if isinstance(scenario_questions, list) else []


def format_mcq_prompt(questions: List[Dict], include_traps: bool = False) -> str:
    """Format MCQ questions into a prompt for the LLM.
    
    Args:
        questions: List of question dictionaries
        include_traps: If True, include trap answer hints (for debugging only)
    """
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
        
        if include_traps and 'trap_answer' in q:
            prompt_parts.append(f"   [DEBUG: trap={q['trap_answer']}, triggered_by={q.get('triggered_by', [])}]\n")

    prompt_parts.append("\nRemember: Respond with ONLY the JSON object, no additional text.")
    return "".join(prompt_parts)


def parse_llm_response(response_text: str) -> Dict:
    """Parse LLM response, handling various JSON formats."""
    response_text = response_text.strip()

    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        response_text = response_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(response_text[start_idx:end_idx])
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse LLM response as JSON: {e}")
        raise ValueError(f"Could not find JSON in LLM response: {e}")


def grade_assessment(questions: List[Dict], llm_answers: Dict) -> Tuple[List[Dict], float]:
    """Grade the assessment programmatically."""
    if "answers" not in llm_answers:
        raise ValueError("LLM response missing 'answers' key")

    answers_list = llm_answers["answers"]
    results = []
    correct_count = 0

    for i, question in enumerate(questions):
        question_num = i + 1
        llm_answer = next(
            (a for a in answers_list if a.get("question_number") == question_num),
            None
        )

        if llm_answer is None:
            results.append({
                "question_number": question_num,
                "question": question["question"],
                "correct_answer": question["correct_answer"],
                "selected_answer": "NOT ANSWERED",
                "is_correct": False,
                "explanation": question["explanation"],
                "reasoning": "No answer provided",
                "trap_answer": question.get("trap_answer"),
                "hit_trap": False
            })
            continue

        selected = llm_answer.get("selected_answer", "").upper().strip()
        correct = question["correct_answer"].upper().strip()
        trap = question.get("trap_answer", "").upper().strip()
        is_correct = (selected == correct)
        hit_trap = (selected == trap) if trap else False

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
            "reasoning": llm_answer.get("reasoning", ""),
            "trap_answer": trap,
            "hit_trap": hit_trap,
            "triggered_by": question.get("triggered_by", [])
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
    """Administer an MCQ pre-test to the AI student."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    questions = get_assessment_questions(scenario_name, knowledge_level)

    if not questions:
        return [], 0.0

    mcq_prompt = format_mcq_prompt(questions)

    test_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": mcq_prompt}
    ]

    if "gpt-5" in model.lower():
        temperature = 1.0

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=test_messages,
        )
        response_text = response.choices[0].message.content.strip()
        llm_answers = parse_llm_response(response_text)
        results, score = grade_assessment(questions, llm_answers)
        return results, score
    except Exception as e:
        raise ValueError(f"Error administering test: {e}")


def summarize_question_learning(
    question_data: Dict,
    conversation_segment: List[Dict[str, str]],
    model: str = "gpt-4o-mini"
) -> str:
    """
    Summarize what the AI student learned for a SPECIFIC question from the teaching conversation.
    
    CRITICAL: This must faithfully capture what was ACTUALLY said, not hallucinate good teaching.
    If the teacher gave poor/wrong/no instruction, the summary must reflect that.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)

    # Extract conversation (exclude system messages)
    conversation = [msg for msg in conversation_segment if msg["role"] != "system"]
    
    if not conversation:
        return "No teaching occurred for this question."

    # Build context about the specific question
    q_text = question_data.get('question', '')
    original_answer = question_data.get('selected_answer', '')
    correct_answer = question_data.get('correct_answer', '')
    original_reasoning = question_data.get('reasoning', '')

    # Format the conversation clearly
    conversation_text = ""
    for msg in conversation[-12:]:  # Last 12 messages
        role = "TEACHER" if msg["role"] == "user" else "AI STUDENT"
        content = msg["content"][:600]
        conversation_text += f"{role}: {content}\n\n"

    prompt = f"""You are analyzing a teaching conversation to summarize what the AI student should have learned.

QUESTION: {q_text}
AI STUDENT'S ORIGINAL ANSWER: {original_answer}
CORRECT ANSWER: {correct_answer}
AI STUDENT'S ORIGINAL REASONING: {original_reasoning}

ACTUAL TEACHING CONVERSATION:
{conversation_text}

YOUR TASK: Summarize ONLY what the teacher ACTUALLY taught. Be completely faithful to what happened.

CRITICAL RULES:
1. ONLY include information the teacher EXPLICITLY stated in the conversation
2. If the teacher said something incorrect, report that they said something incorrect
3. If the teacher gave vague/unclear responses (like "blabla", "ok", etc.), say "The teacher did not provide clear instruction"
4. If the teacher reinforced the student's misconception, say so explicitly
5. DO NOT invent or infer what the teacher "meant" or "should have" said
6. DO NOT add correct information that wasn't in the conversation

Format your response as:
- TEACHER'S INSTRUCTION: [What the teacher actually said/taught - be literal]
- LEARNING OUTCOME: [What the student would reasonably believe after this conversation]
- QUALITY: [Was the teaching clear, unclear, correct, or incorrect?]

Be honest and literal. If the teaching was poor, say so."""

    summary_messages = [
        {"role": "system", "content": "You faithfully summarize conversations without adding information that wasn't present. You never hallucinate or invent content. If teaching was poor or incorrect, you report that honestly."},
        {"role": "user", "content": prompt}
    ]

    temperature = 0.1  # Very low temperature for faithful extraction
    if "gpt-5" in model.lower():
        temperature = 1.0

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=summary_messages,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Learning session completed. (Summary error: {e})"


def administer_enhanced_test(
    scenario_name: str,
    conversation_history: List[Dict[str, str]],
    system_prompt: str,
    knowledge_level: str = "beginner",
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    question_learning_data: Optional[Dict[int, Dict]] = None,
    misconceptions: Optional[List[str]] = None
) -> Tuple[List[Dict], float, str]:
    """
    Administer a post-test with per-question learning context.
    
    Key behavior:
    - Apply whatever was taught, even if incorrect (realistic learning)
    - If teacher taught wrong info, student learns wrong info
    - If teaching was vague/empty, student keeps original understanding
    - Untaught questions use original misconceptions
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    questions = get_assessment_questions(scenario_name, knowledge_level)

    if not questions:
        return [], 0.0, ""

    question_learning_data = question_learning_data or {}
    misconceptions = misconceptions or []
    
    # Build the per-question context
    taught_questions = set(question_learning_data.keys())
    all_question_nums = set(range(1, len(questions) + 1))
    untaught_questions = all_question_nums - taught_questions

    # Create the post-test prompt
    prompt_parts = [
        "# POST-TEST INSTRUCTIONS\n\n",
        "You are an AI student taking a post-test. Apply what you learned from your teacher.\n\n"
    ]

    # Section 1: Questions you were taught
    if taught_questions:
        prompt_parts.append("## QUESTIONS YOU DISCUSSED WITH YOUR TEACHER\n\n")
        prompt_parts.append("For each question, apply what your teacher taught you. If they gave you new information, use it.\n")
        prompt_parts.append("If they only said vague things (like 'blabla'), your understanding didn't change - use your original beliefs.\n\n")
        
        for q_num in sorted(taught_questions):
            learning_data = question_learning_data.get(q_num, {})
            learning_summary = learning_data.get('learning_summary', '')
            prompt_parts.append(f"**Question {q_num}** - What your teacher told you:\n{learning_summary}\n\n")
    
    # Section 2: Questions you were NOT taught
    if untaught_questions:
        prompt_parts.append("## QUESTIONS YOU DID *NOT* DISCUSS\n\n")
        prompt_parts.append(f"For questions {sorted(untaught_questions)}, you received NO teaching.\n")
        prompt_parts.append("Answer based on your ORIGINAL beliefs:\n")
        for m in misconceptions:
            prompt_parts.append(f"- {m}\n")
        prompt_parts.append("\n")

    # Section 3: The actual questions
    prompt_parts.append("---\n\n")
    prompt_parts.append(format_mcq_prompt(questions))

    full_prompt = "".join(prompt_parts)

    # System prompt - apply teaching, don't evaluate it
    post_system_prompt = """You are an AI student taking a post-test.

RULES:
1. For taught questions: Apply what your teacher said. If they said something is "continuous", believe it's continuous. If they said something is "categorical", believe it's categorical. You trust your teacher.
2. If teacher only gave vague/empty responses (like "blabla", "ok"), your understanding didn't change - use your original beliefs.
3. For untaught questions: Use your original misconceptions.

Your "reasoning" field should be YOUR thinking as a student (e.g., "I think ProductID is continuous because my teacher said the range is infinite"), NOT meta-commentary about teaching quality.

Respond with valid JSON only."""

    test_messages = [
        {"role": "system", "content": post_system_prompt},
        {"role": "user", "content": full_prompt}
    ]

    if "gpt-5" in model.lower():
        temperature = 1.0

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=test_messages,
            max_tokens=1500
        )
        response_text = response.choices[0].message.content.strip()
        llm_answers = parse_llm_response(response_text)
        results, score = grade_assessment(questions, llm_answers)

        # Build combined learning summary for display
        combined_summary = ""
        if question_learning_data:
            combined_summary = "## What happened during teaching:\n\n"
            for q_num in sorted(question_learning_data.keys()):
                learning_data = question_learning_data[q_num]
                q_text = learning_data.get('question_text', '')[:80]
                summary = learning_data.get('learning_summary', 'No summary available')
                combined_summary += f"### Question {q_num}: {q_text}...\n{summary}\n\n"

        return results, score, combined_summary

    except Exception as e:
        raise ValueError(f"Error administering post-test: {e}")


def calculate_improvement(pre_test_score: float, post_test_score: float) -> Dict[str, any]:
    """Calculate improvement metrics between pre and post test."""
    improvement = post_test_score - pre_test_score
    return {
        "pre_test_score": round(pre_test_score, 1),
        "post_test_score": round(post_test_score, 1),
        "improvement": round(improvement, 1),
        "improvement_percent": round(improvement, 1),
        "learned": improvement > 10,
    }
