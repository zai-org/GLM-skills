# Seed Data Generation Guide

Seed data is the bridge between static prototypes and a living application. Poor seed data
makes even a well-built app look broken. Great seed data makes it look production-ready.

## Extraction Process

### Step 1: Content Transcription

For each prototype image, extract ALL visible content:

**Text content:**
- Page titles and headings
- Navigation menu items
- Button labels
- Form field labels and placeholder text
- Table headers and cell values
- Card titles, descriptions, prices
- Status labels, tags, badges
- Footer text
- Any visible numbers, dates, percentages

**Visual content:**
- Number of items in lists/grids (exact count)
- Image descriptions (what each image shows)
- Icon types used
- Color-coded status indicators

### Step 2: Data Modeling

Map extracted content to database entities:

```
Prototype Card "iPhone 15 Pro - ¥8999 - 128GB"
  → products table:
    name: "iPhone 15 Pro"
    price: 8999.00
    spec: "128GB"
    image: "resources/iphone15pro.jpg"  (if exists)
```

### Step 3: Relationship Building

- If a product card shows a category badge, create the category and link them
- If a user avatar appears next to a comment, create the user and the comment
- If a table shows order status, create orders with the matching statuses

### Step 4: Volume Matching

- If the prototype shows 8 product cards, create exactly 8 products
- If a pagination shows "1-10 of 47", create 47 items
- If a sidebar shows 5 categories, create exactly 5 categories

## Common Patterns

### E-commerce
```json
{
  "categories": ["Electronics", "Clothing", "Home", "Sports"],
  "products": [
    {
      "name": "Exact name from prototype",
      "price": "Exact price from prototype",
      "image": "resources/product1.jpg or matching resource file",
      "description": "Description visible in prototype or inferred",
      "category": "Matching category from prototype filter"
    }
  ]
}
```

### Dashboard
```json
{
  "stats": {
    "total_users": 12847,    // exact number from prototype stat card
    "revenue": "¥2,384,500", // exact from prototype
    "growth": "+12.5%"       // exact from prototype
  },
  "chart_data": [...],       // data that would produce the chart shape shown
  "recent_activity": [...]   // exact items from activity list
}
```

### Content/Blog
```json
{
  "posts": [
    {
      "title": "Exact title from prototype",
      "excerpt": "Exact preview text visible",
      "author": "Name shown on prototype",
      "date": "Date shown on prototype",
      "cover_image": "resources/blog1.jpg",
      "tags": ["tag1", "tag2"]  // tags visible on prototype
    }
  ]
}
```

## Quality Checks

Before finalizing seed data:
- [ ] Every visible text in prototypes has a corresponding data entry
- [ ] Item counts match prototype exactly
- [ ] All resource files are referenced somewhere
- [ ] Relationships are consistent (no orphan foreign keys)
- [ ] Dates are realistic and consistent
- [ ] Numbers/statistics match prototype values
- [ ] No placeholder text ("Lorem ipsum", "test", "sample")
- [ ] Character encoding is correct (Chinese characters, special symbols)
