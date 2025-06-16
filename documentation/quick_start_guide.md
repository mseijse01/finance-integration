# Quick Start Guide - New Features

This guide covers the recently implemented features for automated scheduling, performance optimization, and improved code organization.

## **Automated ETL Scheduling**

### **Check Data Freshness**
```bash
python scripts/schedule_etl.py --check-freshness
```
Shows how old your data is for each stock symbol.

### **Manual Data Updates**
```bash
# Update all stocks
python scripts/schedule_etl.py --run-once

# Update specific stocks
python scripts/schedule_etl.py --run-once --symbols SBUX KDP
```

### **Set Up Automated Daily Updates**
```bash
# Get cron setup instructions
python scripts/schedule_etl.py --create-cron

# Or run as continuous daemon
python scripts/schedule_etl.py --daemon
```

### **Monitor Automated Runs**
```bash
# View ETL logs
tail -f /tmp/etl_scheduler.log

# Check current cron jobs
crontab -l
```

## **Performance Optimization**

### **Deploy Database Indexes**
```bash
# Add performance indexes (run once)
python scripts/add_performance_indexes.py
```
**Expected improvement:** 50-70% faster database queries

### **Database Schema Migration**
```bash
# Fix schema compatibility issues (if needed)
python scripts/migrate_database_schema.py
```

## **Chart Utilities**

### **Using the New Chart Functions**
```python
from utils.charts import (
    create_stock_comparison_chart,
    add_stock_price_trace,
    get_stock_colors,
    downsample_chart_data
)

# Create a chart
fig = create_stock_comparison_chart(timeframe="6m")

# Get color scheme
colors = get_stock_colors()
print(colors["SBUX"])  # "#00704A"

# Optimize large datasets
optimized_data = downsample_chart_data(large_dataset, target_points=100)
```

## **Troubleshooting**

### **ETL Issues**
```bash
# Check if ETL is working
python scripts/schedule_etl.py --run-once --symbols SBUX

# View detailed logs
tail -f /tmp/etl_scheduler.log
```

### **Performance Issues**
```bash
# Verify indexes were created
python scripts/add_performance_indexes.py

# Check database schema
python scripts/migrate_database_schema.py
```

### **Cron Issues**
```bash
# Check if cron job exists
crontab -l

# Remove cron job if needed
crontab -r

# Check system logs (macOS)
log show --predicate 'process == "cron"' --last 1h
```

## **Configuration**

### **Changing ETL Schedule**
```bash
# Edit cron job
crontab -e

# Example: Run at 2:30 PM daily
30 14 * * * /path/to/python /path/to/schedule_etl.py --run-once >> /tmp/etl_scheduler.log 2>&1
```

### **Adding New Stocks**
1. Add symbol to `COFFEE_STOCKS` list in `scripts/schedule_etl.py`
2. Update dashboard configuration
3. Run manual ETL to populate data

### **Customizing Chart Colors**
Edit the `get_stock_colors()` function in `utils/charts.py`:
```python
def get_stock_colors():
    return {
        "SBUX": "#00704A",  # Starbucks Green
        "YOUR_SYMBOL": "#FF5733",  # Your custom color
        # ... other symbols
    }
```

## **Monitoring & Maintenance**

### **Daily Checks**
- Data freshness: `python scripts/schedule_etl.py --check-freshness`
- ETL logs: `tail /tmp/etl_scheduler.log`
- System performance: Monitor dashboard load times

### **Weekly Maintenance**
- Review ETL success rates in logs
- Check database performance
- Update API keys if needed

### **Monthly Tasks**
- Review and clean old log files
- Update dependencies: `pip install -r requirements.txt --upgrade`
- Backup database

## **Next Steps**

After implementing these features, consider:
1. **Redis caching** for even better performance
2. **Real-time data streaming** with WebSockets
3. **Additional data sources** (Alpha Vantage, SEC filings)
4. **Advanced analytics** (technical indicators, ML predictions)

For more detailed information, see the full documentation in the `documentation/` folder. 