# Chart and table design guidelines

**Project:** 1.2% GPM analysis, 2020-2025  
**Theme:** ColorblindSafe-Longer  
**Reviewed:** 24 September 2026  
**Scope:** Notebook charts, exported figures, HTML heatmaps and future Power BI views.

This document sets project design rules. The theme JSON and analytical definitions remain unchanged. The latest presentation preferences below supersede the earlier defaults: solid bars, minimal gridlines, lighter parenthetical text and numbers without unnecessary trailing zeros. These preferences are implemented in the shared chart helpers and notebook plotting cells. Population and metric definitions are documented in [METHODOLOGY.md](METHODOLOGY.md).

## 1. Design priorities

The [Fuselab Creative article](https://fuselabcreative.com/data-visualization-best-practices/) informs the overall approach: choose a visual for a specific reader question, distinguish numerical correctness from ease of interpretation, maintain consistent color meaning, remove decoration, and review the result with an unfamiliar reader. Its guidance also emphasizes clear tables, visible missingness and uncertainty, and disclosure of interactive filter state.

The rules below adapt those principles to this project's data and theme. They are not a reproduction of the article or a claim that every recommendation is a universal standard. Accessibility requirements are supported separately by W3C references; numerical sizing recommendations are project defaults.

The design priorities, in descending order, are:

1. Numerical integrity and faithful comparison.
2. Readable, accessible values, categories and limitations.
3. Consistent theme colors and semantic roles.
4. Consistent layout and typography.

A theme name is not an accessibility certification. Palette membership does not justify an unreadable label.

## 2. Project theme and color roles

The original theme file, `ColorblindSafe-Longer.json`, and [config/chart_style.json](config/chart_style.json) contain the same theme values at this review. The project file is the runtime source. [src/chart_style.py](src/chart_style.py) maps these values to plotting roles.

| Theme value | Hex | Project use |
| --- | --- | --- |
| Background | `#FFFFFF` | Figure, plotting area and table background |
| Foreground / palette 1 | `#074650` | Default text, primary bars and main series |
| Palette 2 | `#009292` | Secondary comparison series |
| Table accent / palette 3 | `#FE6DB6` | Selective emphasis; not every table cell |
| Palette 4 | `#FEB5DA` | Zero-growth midpoint in existing growth heatmaps |
| Palette 5 | `#480091` | Decline in growth views |
| Palette 6 | `#B66DFF` | Additional categorical series when needed |
| Palette 7 | `#B5DAFE` | Additional categorical fill; needs contrast checks |
| Palette 8 | `#6DB6FF` | Additional categorical series when needed |
| Palette 9 | `#914800` | Additional categorical series when needed |
| Palette 10 | `#23FD23` | Positive growth in growth views |

Implementation-only utility colors are `#F2F2F2` for unavailable heatmap values and black/white for contrast-safe text. These are not additional JSON palette entries. Heatmap headers and recipient labels use black on white; ordinary chart text uses the theme foreground.

A single numerical series uses one primary color. Municipality names identify bars without requiring a separate hue for every location. Repeated categorical comparisons use explicit label-to-color mappings, so sorting does not change category meaning. Decline, neutral and growth colors retain their semantic roles within growth views.

Bars and legend swatches have uniform, solid fills, including grouped and stacked bars. Hatching, stripes, dots, textures and decorative internal lines are excluded. Outlines are absent by default; a thin perimeter is reserved for light fills that need a visible boundary. Legend swatches match the plotted fills.

The categorical palette is not a continuous numerical scale. The JSON specifies colors, not a font, font size, chart aspect ratio or statistical method.

## 3. Contrast and non-color cues

Normal-sized text should meet 4.5:1 contrast against its background; large text has a 3:1 threshold. W3C defines large text as at least 18 pt regular or 14 pt bold. Contrast assessment applies at the final displayed size, including any image reduction. [W3C text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)

The following ratios were calculated from this palette using sRGB relative luminance. They assume opaque fills; displayed ratios are rounded, but pass/fail decisions must use unrounded values.

| Fill | Black text contrast | White text contrast | Use for normal-sized labels inside this fill |
| --- | ---: | ---: | --- |
| `#074650` | 2.00:1 | 10.50:1 | White |
| `#009292` | 5.53:1 | 3.80:1 | Black |
| `#FE6DB6` | 8.08:1 | 2.60:1 | Black |
| `#FEB5DA` | 12.84:1 | 1.64:1 | Black |
| `#480091` | 1.68:1 | 12.47:1 | White |
| `#B66DFF` | 6.62:1 | 3.17:1 | Black |
| `#B5DAFE` | 14.42:1 | 1.46:1 | Black |
| `#6DB6FF` | 9.79:1 | 2.15:1 | Black |
| `#914800` | 3.13:1 | 6.71:1 | White |
| `#23FD23` | 15.15:1 | 1.39:1 | Black |

The white-text column also gives each opaque color's contrast against a white canvas. Bright green and pale fills should not be the sole means of locating an essential thin mark on white. A dark perimeter, readable marker or stronger theme color provides an alternative where needed. Essential graphical boundaries generally need 3:1 contrast against adjacent colors, subject to the criterion's exceptions. This is separate from the text test. [W3C non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)

Meaning is conveyed through more than color: growth signs and values, line names, and distinct markers or line styles. Grayscale and color-vision-deficiency checks complement accessible data tables and text descriptions. A tooltip alone is not an adequate substitute for visible category meaning. [W3C use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)

For bars, non-color identification comes from direct series labels, a clearly labeled left/right series order, or labeled separate panels. A color-only legend is not sufficient when the bars cannot otherwise be distinguished. Distinct markers and solid/dashed styles remain appropriate for line charts; the ban on extra lines applies to bar fills, not to meaningful line-series styles.

Gradient label colors depend on the actual rendered background, not just the endpoint colors. Black heatmap headers do not require black text on every colored cell. Where black text is required, an opaque white label background or uncolored numeric companion table preserves readability without changing the theme's purple anchor.

## 4. Visual selection by analytical question

These are project defaults, not automatic chart selections:

| Project question | Preferred view | Essential context |
| --- | --- | --- |
| Which municipalities receive more recorded funding? | Sorted horizontal bars | Recipient location; period; funding scope; unique-recipient count |
| How did annual funding change? | Line with annual markers | Every calendar year; gaps; nominal EUR |
| How are funding amounts distributed? | Histogram with log-spaced edges for positive skewed amounts | Recipient-year unit; excluded zero/missing count; bin count |
| How do growth distributions differ by age or legal form? | Boxplots plus valid counts | Age reference year; median and quartiles; outlier convention |
| How does growth relate to starting funding? | Scatter plot | Baseline year; log-axis exclusions; no causal title |
| How frequent are the three growth patterns? | Bars of counts or shares | Comparable growing recipients as denominator |
| How many euros changed within each pattern? | Diverging horizontal bars | Common zero; separate declining/unchanged groups |
| How do available-pair and stable samples differ? | Small-multiple line charts | Same percentage scale; both sample counts |
| Which recipient changed in which year? | Scrollable heatmap with values | Growth definition; missing marker; full export |
| What explains the difference in recorded endpoint totals? | Presence-group table, optionally a reconciled waterfall | Observed contributions, not imputed individual growth |

Municipality names do not form a time sequence, so their comparison uses bars rather than a connecting line. Funding and recipient counts appear as funding bars with smaller count annotations or as aligned separate panels. Arbitrarily scaled dual axes can suggest relationships that depend on presentation choices rather than data.

No demographic source is used in this project. Municipality rankings therefore are not population-normalized. A geographic map is optional when location itself is the question; it is not a substitute for a readable ranking of funding totals.

## 5. Axes, layout and numerical integrity

Bars encode length: ordinary funding/count bars start at zero, and signed-change bars extend on both sides of zero. Lines and scatter plots may use a restricted range when it is explicit and useful. Comparable panels should share scales. Restrained borders and grids, horizontal category labels where practical, and nearby annotations support readability. The final rendering, not a nominal font size, determines legibility. [Government Analysis Function chart guidance](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-charts/)

Project-specific requirements:

- Filled chart shapes have **no border outlines**: bars, stacked segments, histogram bins, filled areas and their legend swatches use `edgecolor="none"` and `linewidth=0`. Light fills do not receive automatic dark outlines. Distinguish groups through theme colors, labels and spacing, not strokes or hatching. This supersedes earlier histogram-separator exceptions. Axis lines, line-series paths, boxplot medians/whiskers and meaningful reference lines remain visible; they convey information rather than framing fills.
- Line-chart markers have readable value labels, in addition to labeled axis ticks. Labels use the numerical axis units (for example percentages or EUR), omit missing points, and retain explicit caller-supplied positions. The shared `finish_chart` adds labels to marked line series when absent; it does not label every scatter observation or boxplot outlier. Dense comparisons should use separate panels if labels cannot fit, rather than silently dropping observations.
- Zero is a meaningful reference, not a background grid. Where zero is inside a linear value axis, a thin light reference line marks it: theme foreground, alpha 0.25, width 0.8, behind the data. Horizontal bars use a vertical zero line. Existing zero references are lightened rather than duplicated. A logarithmic axis receives no zero line, and a zoomed line chart is not forced to include zero. Deliberate exceptions can use `finish_chart(..., point_labels=False, zero_reference=False)` and should explain the reason.

- Charts start without gridlines: `ax.grid(False, which="both")`. Where a grid materially aids comparison, it consists of about three to five faint major reference levels on the numerical axis only. Minor grids are absent by default. Directly labeled charts generally need no grid; meaningful zero and reference lines remain distinct from decorative grids.
- Log axes are labeled explicitly. Zero and negative values are excluded from conventional log axes and their counts are reported separately. A logarithmic x-axis does not repair equal-width histogram bins.
- Calendar years are evenly spaced, with reindexing to the full year range preserving breaks for absent observations. A dashed bridge is permitted only as a visibly explained connector between observed endpoints, not evidence of intermediate annual values.
- For percentage growth, zero means no change and -100% means a positive amount fell to recorded zero. A missing baseline is not zero growth.
- A difference between 40% and 53% is 13 percentage points. It is not a 13% relative increase.
- Qualifying-year and all-year funding are overlapping scopes, not additive categories.
- The separate persistence-funding charts use common axes so their heights remain comparable.
- Rankings follow the displayed measure. Time periods and age bands retain their natural order, with Unknown last. Top-N views identify the selection limit and retain a full table; any Other category has an explicit definition.

## 6. Typography and spacing defaults

The following extend the JSON rather than coming from it. They are starting points for a notebook figure shown near its intended size:

| Element | Starting setting |
| --- | --- |
| Typeface | DejaVu Sans in Matplotlib; Segoe UI in Power BI; sans-serif fallback |
| Figure title | 14-16 pt, left aligned |
| Axes and tick labels | 10-12 pt |
| Value labels and recipient counts | 9-11 pt; enlarge if exported smaller |
| Line width / point marker | 1.5-2 pt / 4-6 pt |
| Standard figure | About 9 by 5 inches; adapt to labels and purpose |
| Long horizontal ranking | About 0.35-0.45 inches of height per category, plus title/axis space |
| Export | SVG/PDF for scalable figures where suitable; PNG at 200-300 dpi for raster delivery |

Related figures share typography. Figure dimensions accommodate category names and data density rather than a fixed page-filling target. Long names wrap at word boundaries, with full names retained in companion tables. Export review includes Lithuanian characters.

### Parenthetical text

Parenthetical annotations, including their parentheses, use a lighter shade of the surrounding text color in titles, axes, categories, legends, captions and table annotations. Examples include `(n=123)`, `(n = unique recipients)`, `(latest observed year)` and `(log scale)`. The main text retains its normal color; only the parenthetical portion is lightened.

The secondary text color is an opaque tint of the same base color rather than an unrelated palette hue. Ordinary annotations derive from the theme foreground; black headings can use a lighter neutral. The tint is limited by a 4.5:1 contrast requirement against the actual background. Where no lighter shade passes, the original contrast-safe color remains. This derived text role does not modify the JSON palette.

Parenthetical counts can be one point smaller than the main label, but never below the project's readable 9 pt default. Counts can appear on a separate line for easier scanning. Differently colored portions require segmented text rendering; setting a whole tick label's color cannot style only a parenthetical substring. Mathematical grouping symbols in a formula are not secondary explanatory annotations and must remain legible as part of the formula.

A value label that cannot fit outside a large bar may appear inside that bar with contrast-safe text; other labels remain outside. Layout allowance reflects actual label extents rather than a fixed percentage margin. Smaller recipient counts remain readable.

## 7. Titles, labels, units and wording

Project title template: **measure + recipient population + period**. Captions provide exclusions and reference years. Finding-led titles require support from the actual results.

| Avoid | Prefer |
| --- | --- |
| Richest supporters | Average calculated PMD per recorded request |
| Returning vs newcomers, when Other is broader | 2025 top 1%: persistent vs other recipients |
| Growth by age | Funding growth 2020-2025 by organization age in 2025 |
| Municipalities donating the most | Funding received by organizations registered in each municipality |
| Total funding, when only qualifying years count | Funding received during top-1% years |
| Percentage growth for a natural-log ratio | Log growth, ln(ending / starting funding) |

Count labels distinguish unique recipients, recipient-years, requests and valid comparisons. Requests are not automatically unique supporters. A request count beside a recipient name includes its year and unit, for example `Organization A (2025 requests: 120)`.

Default maximum precision: integer counts; one decimal for displayed percentages; one or two decimals for log ratios as needed; whole EUR for large rankings and up to two decimals for per-request values. Chart ticks, value labels, legends and presentation tables omit unnecessary trailing zeros and empty decimal separators. Fixed decimal places may be retained in an explicitly designated audit/accounting export when required, not as the default chart format. Calculations retain their full precision. Statistical counts are not currency. Thousands separators and decimal conventions are consistent, with EUR or million EUR stated in headers and repeated beside values only where needed for clarity.

This is removal of redundant decimal places, not rounding upward with `ceil`. Meaningful decimals remain at the chosen precision. Small nonzero amounts require enough precision, or a smaller unit, to remain distinguishable from zero. Numeric formatting precedes the unit suffix; comparable panels share the same policy. A rounding-produced `-0` is displayed as `0`.

| Before | Preferred display |
| --- | --- |
| `70.0M EUR` | `70M EUR` |
| `70.80M EUR` | `70.8M EUR` |
| `21.65M EUR` | `21.65M EUR` |
| `0.0` | `0` |
| `35.0%` | `35%` |
| `35.5%` | `35.5%` |
| `1,234.00 EUR` | `1,234 EUR` |
| `0.01 EUR` | `0.01 EUR`, not `0 EUR` |

## 8. Tables, legends and heatmaps

Ordinary tables left-align names and right-align numbers. Precision, sorting and totals support the comparison. Direct series labels are preferred where space allows; otherwise a nearby legend follows a consistent order. Decorative gradients, shadows and 3D perspective are excluded. [Fuselab chart and table guidance](https://fuselabcreative.com/data-visualization-best-practices/)

Project heatmap requirements:

- The semantic anchors are purple decline, pale pink neutral, green growth. Missing uses light grey, plus a text marker such as `Unavailable`, not a blank indistinguishable from an empty row.
- Zero is the neutral midpoint. Values crossing zero use diverging normalization; magnitude-only measures require a sequential scale. Matplotlib separates normalization from the colormap, including explicit center control. [Matplotlib normalization](https://matplotlib.org/stable/users/explain/colors/colormapnorms.html)
- The purple/pink/green combination is the project's existing theme choice, not a guaranteed perceptually uniform ramp. Signed numeric labels provide exact values; color intensity alone is not a precise magnitude measure.
- Scale descriptions state units, bounds, clipping and any differences between annual and whole-period columns. Recipient rows are not independently rescaled.
- Previews and full exports share a scale. The first 30 ordered rows are identified as a preview, not a representative sample.
- Sticky names and column headings support scrolling. Complete HTML exports contain large tables, while notebooks retain compact previews.
- For heatmap cells, centered values may support the grid layout; a conventional right-aligned numeric companion table supports precise column comparison. This is an intentional exception to the ordinary-table rule.
- Codes remain internal identifiers. Names may be display labels, but duplicate names must still correspond to separate code-keyed rows.

The shared heatmap helper selects black or white cell text from the rendered background's contrast ratio. Headers remain black on white. Unavailable cells use light grey with an explicit text label, and an expandable numeric table provides exact values without color. Automated tests cover all 256 gradient colors and the theme palette.

## 9. Missingness, uncertainty and sample definitions

The project's statuses distinguish missing endpoints, invalid denominators and recorded zero funding rather than replacing unavailable comparisons with zeros. Unknown age includes missing or inconsistent dates; the status field preserves the reason. Unknown remains visible in age comparisons.

Annual pattern shares are accompanied by comparable and growing counts for each pair. Stable-sample eligibility can be fixed while the number growing varies. Municipality log-growth summaries report valid log-growth counts, with the minimum sample rule applied to those observations rather than all recipients.

Administrative records are not automatically a random sample. Recorded totals do not receive generic confidence intervals. Any interval associated with a statistical estimate, forecast or model requires a stated method and interpretation. A bootstrap ranking-stability exercise does not resolve systematic missingness or prove causation. Boxplot whiskers are not confidence intervals unless explicitly calculated as such.

Selection rules belong near rankings: top five by which measure, in which year, and subject to which threshold? A chart selected using 2025 values describes that selected group; it is not an unbiased picture of all recipients' historical trajectories.

## 10. Notebook, export and Power BI workflow

1. Each chart has a defined question, population, period, unit and missingness rule, based on validated inputs.
2. Shared helpers load `config/chart_style.json` and expose named color roles.
3. Chart-specific formatting preserves category meaning and accessible contrast.
4. Charts and supporting tables share filters. Interactive-view specifications include visible cohort, year and top-N selections plus a reset action.
5. Descriptions and exact values complement the visual. Interactive reports require keyboard access, logical reading order, visible focus and alternatives to hover-only information.
6. Visual review covers notebooks, full HTML reports and exports at normal size, including long names, extreme values, negative values and Unknown categories.
7. Code changes require fresh notebook execution and refreshed reproducibility records before publication. A documentation-only change does not imply that existing charts now comply.

A future Power BI report can use the same JSON theme, with visual formatting reviewed separately. Palette import does not configure the project's semantic growth mapping, axis rules, missing-value behavior, accessible labeling or statistical samples automatically. Matplotlib settings do not necessarily have direct Power BI equivalents.

## 11. Chart release checklist

### Shared implementation for new charts

Notebook setup loads and applies the project theme. The common finishing entry point is `finish_chart(fig, note)` from `src/chart_style.py`. The note should identify the population, years, units and exclusions. The helper cannot decide whether the underlying comparison is valid. It removes bar hatching, does not add gridlines, and preserves explicitly requested major reference grids. Notebook charts start with their grids disabled. It trims trailing decimal zeros from numerical axes and value annotations, and renders explanatory parenthetical text with a contrast-checked lighter tint while retaining the original label layout. `format_number(...)` formats number labels, while `secondary_text_color(...)` supports individually positioned secondary annotations. Heatmap values use the same number-formatting policy.

`contrast_text(fill_color)` determines text color inside bars. `growth_boxplot(...)` renders the fixed-period log-growth distributions, while `render_growth_heatmap(...)` maintains shared preview/export scales, missing-value labels and contrast-safe cell text. Different metrics or time windows require corresponding labels and sample definitions.

The project retains the combined persistence chart and both separate charts, with a common scale for the separate pair. Long group comparisons use horizontal layouts. Multiple bar series use solid fills with explicit series identification; multiple line series can use distinct line/marker combinations in addition to color. Automated checks complement, but do not replace, visual inspection or accessibility testing with readers.

### Reference example: funding by top-1% persistence

The persistence chart illustrates these conventions without changing the data, group order, funding scopes or zero baseline:

1. Bars and legend swatches use solid primary and secondary theme fills.
2. The chart has no grid by default; a few faint major reference lines remain an option where needed.
3. Streak numbers `1` through `6` use the normal foreground. Each `(n=...)` appears beneath its number in a lighter, contrast-checked tint.
4. The axis explanation `(n = unique recipients)` uses the same lighter treatment, without duplicating that definition in the footer.
5. Ticks such as `0`, `10`, `20` and `70` accompany the axis title `Calculated PMD, million EUR`. Compact unit-bearing ticks are an alternative, with redundant `.0` omitted.
6. Legend labels identify `Left bar: during top-1% years` and `Right bar: all analysis years`, making the comparison understandable without hue.
7. A short scope note states: `2020-2025. Funding during top-1% years is included in all-year funding; do not add the two totals.`

The existing two separate funding charts remain available and must keep the same numerical scale. These are display changes, not changes to amounts, persistence definitions or sample sizes.

- [ ] One clear reader question, with population and years stated.
- [ ] Counts, amounts, rates and denominators match the supporting table.
- [ ] Correct annual/fixed-period and qualifying-year/all-year scope.
- [ ] Theme colors retain their meanings; no automatic color reassignment after sorting.
- [ ] Text passes contrast checks on actual backgrounds; meaning does not depend only on hue.
- [ ] Parenthetical annotations are lighter versions of the same text color and remain readable.
- [ ] Filled shapes and legend swatches have solid fills without border outlines, hatching or decorative internal lines, including light-colored bars.
- [ ] Gridlines are absent unless justified; any retained grid is sparse, faint and major-only.
- [ ] Unnecessary trailing decimal zeros are removed without changing the underlying values.
- [ ] Axes, log exclusions and zero baselines are appropriate to the encoding.
- [ ] Missing values and Unknown categories are visible and distinguishable from zero.
- [ ] Valid sample counts accompany growth comparisons and subgroup summaries.
- [ ] Labels, legends, units and long names are readable without clipping.
- [ ] Preview/full export scales match, and the complete data remains accessible.
- [ ] Related charts use comparable scales and clearly identify different samples.
- [ ] An unfamiliar reader can identify the question and main comparison without coaching.

## 12. Presentation review priorities

1. Solid bar fills, restrained grids, unchanged theme colors and meaningful reference lines.
2. Consistent number formatting and contrast-checked lighter parenthetical labels.
3. Consistency between the persistence-chart example, other charts and their legend swatches.
4. Contrast-safe heatmap text, black headers and explicit unavailable values; identifiable light marks without patterned fills.
5. Clear samples, units, periods and age reference years, with count annotations rather than arbitrary dual axes.
6. Readable labels, comparable paired-chart scales and verified exports. Fresh execution and reproducibility records identify the tested notebook versions after implementation changes.

This is a design policy and review guide. Statistical definitions remain in [METHODOLOGY.md](METHODOLOGY.md); tested execution remains documented in [REPRODUCIBILITY.md](REPRODUCIBILITY.md). Sources were consulted on 24 September 2026 and linked next to the rules they support.
