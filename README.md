# Production Planning App for ERPNext

A custom ERPNext application for intelligent production planning and queuing across multiple manufacturing units.

## Features

### 🎯 Intelligent Unit Allocation
- Automatic unit assignment based on quality grades and GSM values
- Configurable quality-to-unit mapping rules
- Real-time capacity checking

### 📊 Capacity Management
- Track day and night shift capacities for each unit
- Monitor current queue weight and available capacity
- Automatic capacity calculations and updates

### 🔄 Queue Management
- Automatic queue positioning based on delivery dates and priorities
- Real-time queue status visibility
- Production progress tracking

### 📈 Quality-Based Routing

| Unit | Quality Grades | GSM Criteria |
|------|---------------|--------------|
| Unit 1 | SUPER PLATINUM, PLATINUM, PREMIUM, GOLD, SUPER CLASSIC | > 50 |
| Unit 2 | GOLD, SILVER, BRONZE, CLASSIC, ECO SPECIAL, ECO SPL | > 20 |
| Unit 3 | SUPER PLATINUM, PLATINUM, PREMIUM, GOLD, SILVER, BRONZE | > 10 |
| Unit 4 | Other qualities | > 10 |

## Screenshots

[Add screenshots of your Planning Sheet interface here]

## Installation

### For ERPNext Cloud Users

1. **Fork this repository** to your GitHub account

2. **Install the app** on your Frappe Cloud site:
   - Go to your site dashboard on Frappe Cloud
   - Navigate to Apps section
   - Click "Install App"
   - Enter your forked repository URL
   - Wait for installation to complete

3. **Run migrations**:
   ```bash
   bench --site your-site-name migrate
   ```

### For Self-Hosted ERPNext

1. **Get the app**:
   ```bash
   cd ~/frappe-bench
   bench get-app https://github.com/yourcompany/production_planning.git
   ```

2. **Install on site**:
   ```bash
   bench --site your-site-name install-app production_planning
   ```

3. **Restart bench**:
   ```bash
   bench restart
   ```

## Initial Setup

### 1. Configure Unit Capacities

Navigate to: **Production Planning > Unit Capacity > New**

Create a record for each unit with their capacities:

```
Unit 1:
- Day Shift Capacity: 5000 KG
- Night Shift Capacity: 4000 KG

Unit 2:
- Day Shift Capacity: 4500 KG
- Night Shift Capacity: 3500 KG

Unit 3:
- Day Shift Capacity: 4000 KG
- Night Shift Capacity: 3000 KG

Unit 4:
- Day Shift Capacity: 3500 KG
- Night Shift Capacity: 2500 KG
```

### 2. Set User Permissions

Assign appropriate roles to users:
- **Manufacturing Manager**: Full access
- **Manufacturing User**: Create and edit access

### 3. Start Using

Create your first Planning Sheet:
1. Go to **Production Planning > Planning Sheet > New**
2. Select Sales Order or enter details manually
3. Add items with specifications
4. Click "Get Unit Recommendation"
5. Submit to finalize and add to queue

## Usage Guide

### Creating a Planning Sheet

**From Sales Order**:
```
1. Select Sales Order → Auto-fills customer, delivery date, items
2. Review item details and specifications
3. System auto-allocates appropriate unit
4. Submit to finalize
```

**Manual Entry**:
```
1. Enter Party Code and Customer
2. Add items with full specifications:
   - Item Code, Name
   - Quality, Color, GSM
   - Quantity, Weight, Roll details
3. Get unit recommendation
4. Submit
```

### Monitoring Queue Status

From any Planning Sheet:
- Click **"View Queue Status"** button
- See current capacity utilization
- View all orders in queue
- Check position and estimated production time

### Production Workflow

```
Draft → Finalized → In Production → Completed
```

1. **Draft**: Initial creation and editing
2. **Finalized**: Submitted and added to queue
3. **In Production**: Click "Start Production"
4. **Completed**: Mark as complete when done

## Quality Extraction

The app automatically extracts quality and color from item names using pattern matching:

**Example**:
- Item: "PLATINUM 90 GSM WHITE HDPE BAGS"
- Extracted Quality: "PLATINUM"
- Extracted Color: "WHITE"

### Supported Quality Grades
SUPER PLATINUM, PLATINUM, PREMIUM, GOLD, SILVER, BRONZE, CLASSIC, SUPER CLASSIC, ECO SPECIAL, ECO SPL, ECO GREEN, SUPER ECO, LIFESTYLE, DELUXE, ULTRA, UV

### Supported Colors
WHITE, BLACK, RED, BLUE, GREEN, YELLOW, ORANGE, PINK, MAROON, GREY, BROWN, BEIGE, VIOLET, and various combinations (BRIGHT WHITE, DARK GREY, etc.)

## Excel Import

Prepare Excel file with these columns:
- Party Code
- Customer
- Item Code
- Item Name
- Quality
- Color
- GSM
- Quantity
- Weight per Roll
- No of Rolls
- Delivery Date

Import via: **Data Import > Planning Sheet**

## API / Whitelisted Methods

### Get Unit Queue Status
```python
frappe.call({
    method: 'production_planning.production_planning.doctype.planning_sheet.planning_sheet.get_unit_queue_status',
    args: { unit_name: 'Unit 1' },
    callback: function(r) {
        console.log(r.message);
    }
});
```

### Get Quality-Based Recommendation
```python
frappe.call({
    method: 'production_planning.production_planning.doctype.planning_sheet.planning_sheet.get_quality_based_recommendation',
    args: { quality: 'PLATINUM', gsm: 90 },
    callback: function(r) {
        console.log('Recommended Unit:', r.message);
    }
});
```

## Scheduled Tasks

### Daily (Midnight)
- Reset capacity counters
- Recalculate queue weights
- Update available capacities

### Hourly
- Update production queue
- Check production progress
- Refresh queue positions

## Customization

### Adding New Quality Grades

Edit `planning_sheet.py`:
```python
UNIT_1 = ["SUPER PLATINUM", "PLATINUM", "YOUR_NEW_QUALITY"]
```

### Changing Allocation Rules

Modify the `allocate_unit_to_sheet` method:
```python
if avg_gsm > YOUR_GSM and dominant_quality in YOUR_QUALITY_LIST:
    allocated_unit = "YOUR_UNIT"
```

### Adjusting Capacities

Update via UI:
**Production Planning > Unit Capacity > [Select Unit] > Edit**

## Troubleshooting

### Unit Not Auto-Allocating
- ✓ Check quality name matches predefined list
- ✓ Verify GSM value is numeric
- ✓ Ensure Unit Capacity records exist

### Queue Not Updating
- ✓ Submit the Planning Sheet (docstatus must be 1)
- ✓ Verify unit allocation
- ✓ Check scheduled tasks are running

### Capacity Shows Zero
- ✓ Create Unit Capacity records
- ✓ Verify unit names match exactly
- ✓ Enter capacities as numeric values (KG)

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- **Documentation**: See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
- **Issues**: Report on GitHub Issues
- **Email**: info@yourcompany.com

## License

MIT License - See [LICENSE](license.txt) for details

## Credits

Developed by Your Company for ERPNext ecosystem.

---

**Version**: 0.0.1  
**Compatible with**: ERPNext v14, v15  
**Framework**: Frappe
