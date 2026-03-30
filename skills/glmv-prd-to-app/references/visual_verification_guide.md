# Visual Verification Guide

## Why Visual Verification Matters

The single biggest quality differentiator is whether the built app actually looks like the
prototype. Without systematic comparison, it's easy to accumulate small differences that
collectively make the app feel "off".

## Comparison Methodology

### 1. Side-by-Side Reading

Read both images (prototype and screenshot) using the Read tool. For each, examine:

**Layout Grid (most impactful)**
- Is the overall page structure correct? (sidebar width, header height, content area)
- Are sections in the right order vertically?
- Are columns the right width proportionally?

**Color Palette**
- Background colors match?
- Primary action color matches?
- Text colors match (headings vs body text)?
- Border/divider colors match?

**Typography Hierarchy**
- Heading sizes look proportionally correct?
- Body text size reasonable?
- Font weight variations match? (bold headings, regular body)

**Spacing**
- Card padding looks similar?
- Gaps between elements proportional?
- Page margins match?

**Component Details**
- Button shapes (rounded? square? pill?)
- Card shadows present?
- Border radius consistency?
- Icon presence and placement?

### 2. Priority Matrix

Fix issues in this order:
1. **Critical**: Wrong layout structure, missing sections, broken content
2. **High**: Wrong colors, missing components, data not loading
3. **Medium**: Spacing differences, typography mismatches
4. **Low**: Shadow differences, border radius, minor alignment

### 3. Iteration Limit

Max 3 visual fix iterations per page:
- Iteration 1: Fix critical and high-priority issues
- Iteration 2: Fix medium-priority issues
- Iteration 3: Polish remaining differences

After 3 iterations, move on. Diminishing returns set in quickly.

## Common Discrepancies and Fixes

### Layout is wrong
- Check if using flexbox/grid correctly
- Verify container max-width
- Check sidebar width (usually 240-280px)
- Check header height (usually 56-72px)

### Colors don't match
- Extract hex values from prototype more carefully
- Check if using transparency/opacity where prototype doesn't
- Verify background colors on nested elements

### Content is missing
- Check if API is returning all data
- Verify seed data has all items
- Check if conditional rendering is hiding elements

### Images not showing
- Verify image paths are correct
- Check if static file serving is configured
- Ensure resource files are copied to public directory

### Spacing feels off
- Use browser dev tools values as reference (8px grid system)
- Check if using margin vs padding correctly
- Verify gap values in flex/grid containers

## Screenshot Capture Tips

When using render_page.py:
- Use `--width 1280` for desktop views (matches most prototype widths)
- Use `--width 375` for mobile views
- Use `--wait 3` if the page has animations or lazy loading
- Use `--full-page` to capture the entire scrollable page
- Use `--routes /,/products,/about` to batch-capture all pages
