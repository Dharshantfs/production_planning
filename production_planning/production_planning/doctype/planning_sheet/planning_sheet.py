# -*- coding: utf-8 -*-
# Copyright (c) 2026, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, getdate, add_days
import re

class PlanningSheet(Document):
    def validate(self):
        """Validate planning sheet before saving"""
        self.validate_items()
        self.calculate_totals()
        self.parse_item_details()
    
    def before_save(self):
        """Allocate unit before saving"""
        if not self.allocated_unit:
            self.allocate_unit_to_sheet()
    
    def on_submit(self):
        """Update queue and create work orders on submit"""
        self.update_queue_position()
        self.planning_status = "Finalized"
    
    def validate_items(self):
        """Validate that items are present"""
        if not self.items:
            frappe.throw("Please add at least one item to the Planning Sheet")
    
    def calculate_totals(self):
        """Calculate total quantity and weight"""
        total_qty = 0
        total_weight = 0
        
        for item in self.items:
            # Calculate weight per item if not already set
            if not item.total_weight and item.weight_per_roll and item.no_of_rolls:
                item.total_weight = flt(item.weight_per_roll) * flt(item.no_of_rolls)
            
            total_qty += flt(item.qty)
            total_weight += flt(item.total_weight)
        
        self.total_quantity = total_qty
        self.total_weight = total_weight
        
        # Calculate estimated production days
        if self.allocated_unit and self.total_weight:
            capacity = get_unit_daily_capacity(self.allocated_unit)
            if capacity:
                self.estimated_production_days = flt(self.total_weight / capacity, 2)
    
    def parse_item_details(self):
        """Parse item name to extract quality and color"""
        for item in self.items:
            if item.item_name and not item.quality:
                quality, color = extract_quality_and_color(item.item_name)
                item.quality = quality
                item.color = color
    
    def allocate_unit_to_sheet(self):
        """Allocate unit based on quality, GSM and capacity"""
        # Quality rules
        UNIT_1 = ["SUPER PLATINUM", "PLATINUM", "PREMIUM", "GOLD", "SUPER CLASSIC"]
        UNIT_2 = ["GOLD", "SILVER", "BRONZE", "CLASSIC", "ECO SPECIAL", "ECO SPL"]
        UNIT_3 = ["SUPER PLATINUM", "PLATINUM", "PREMIUM", "GOLD", "SILVER", "BRONZE"]
        
        # Collect all items data
        items_data = []
        for item in self.items:
            items_data.append({
                "quality": item.quality.upper() if item.quality else "",
                "gsm": flt(item.gsm),
                "weight": flt(item.total_weight)
            })
        
        if not items_data:
            return
        
        # Get dominant quality (most common)
        quality_counts = {}
        total_weight = 0
        avg_gsm = 0
        
        for item_data in items_data:
            qual = item_data["quality"]
            if qual:
                quality_counts[qual] = quality_counts.get(qual, 0) + item_data["weight"]
            total_weight += item_data["weight"]
            avg_gsm += item_data["gsm"] * item_data["weight"]
        
        avg_gsm = avg_gsm / total_weight if total_weight > 0 else 0
        dominant_quality = max(quality_counts, key=quality_counts.get) if quality_counts else ""
        
        # Allocate unit based on rules
        allocated_unit = None
        
        if avg_gsm > 50 and dominant_quality in UNIT_1:
            allocated_unit = "Unit 1"
        elif avg_gsm > 20 and dominant_quality in UNIT_2:
            allocated_unit = "Unit 2"
        elif avg_gsm > 10 and dominant_quality in UNIT_3:
            allocated_unit = "Unit 3"
        elif avg_gsm > 10:
            allocated_unit = "Unit 4"
        
        # Check capacity and assign to best available unit
        if allocated_unit:
            capacity_info = frappe.db.get_value("Unit Capacity", 
                                               allocated_unit,
                                               ["day_shift_capacity_kg", "night_shift_capacity_kg", "current_queue_weight"],
                                               as_dict=True)
            
            if capacity_info:
                self.allocated_unit = allocated_unit
                self.unit_capacity_day = capacity_info.day_shift_capacity_kg
                self.unit_capacity_night = capacity_info.night_shift_capacity_kg
                
                # Update item allocation
                for item in self.items:
                    item.allocated_to_unit = allocated_unit
        
        return allocated_unit
    
    def update_queue_position(self):
        """Update queue position based on delivery date and priority"""
        if not self.allocated_unit:
            return
        
        # Get all finalized planning sheets for this unit
        existing_sheets = frappe.get_all("Planning Sheet",
                                        filters={
                                            "allocated_unit": self.allocated_unit,
                                            "planning_status": ["in", ["Finalized", "In Production"]],
                                            "docstatus": 1,
                                            "name": ["!=", self.name]
                                        },
                                        fields=["name", "queue_position", "delivery_date"],
                                        order_by="queue_position asc")
        
        # Calculate new queue position
        if existing_sheets:
            max_position = max([sheet.queue_position or 0 for sheet in existing_sheets])
            self.queue_position = max_position + 1
        else:
            self.queue_position = 1
        
        # Update unit capacity
        update_unit_capacity_usage(self.allocated_unit)


# Utility Functions

def extract_quality_and_color(item_name):
    """Extract quality and color from item name"""
    QUAL_LIST = ["SUPER PLATINUM", "SUPER CLASSIC", "SUPER ECO", "ECO SPECIAL", 
                 "ECO GREEN", "ECO SPL", "LIFE STYLE", "LIFESTYLE", "PREMIUM", 
                 "PLATINUM", "CLASSIC", "DELUXE", "BRONZE", "SILVER", "ULTRA", 
                 "GOLD", "UV"]
    QUAL_LIST.sort(key=len, reverse=True)
    
    COL_LIST = ["GOLDEN YELLOW", "BRIGHT WHITE", "SUPER WHITE", "BLACK", "RED", 
                "BLUE", "GREEN", "MILKY WHITE", "SUNSHINE WHITE", "BLEACH WHITE", 
                "LEMON YELLOW", "BRIGHT ORANGE", "DARK ORANGE", "BABY PINK", 
                "DARK PINK", "CRIMSON RED", "LIGHT MAROON", "DARK MAROON", 
                "MEDICAL BLUE", "PEACOCK BLUE", "RELIANCE GREEN", "PARROT GREEN", 
                "ROYAL BLUE", "NAVY BLUE", "LIGHT GREY", "DARK GREY", 
                "CHOCOLATE BROWN", "LIGHT BEIGE", "DARK BEIGE", "WHITE MIX", 
                "BLACK MIX", "COLOR MIX", "BEIGE MIX", "WHITE"]
    COL_LIST.sort(key=len, reverse=True)
    
    quality = ""
    color = ""
    item_upper = item_name.upper()
    
    # Extract quality
    for qual in QUAL_LIST:
        if qual in item_upper:
            quality = qual
            break
    
    # Extract color
    for col in COL_LIST:
        if col in item_upper:
            color = col
            break
    
    return quality, color


def get_unit_daily_capacity(unit_name):
    """Get total daily capacity for a unit"""
    capacity = frappe.db.get_value("Unit Capacity", 
                                   unit_name, 
                                   ["day_shift_capacity_kg", "night_shift_capacity_kg"],
                                   as_dict=True)
    
    if capacity:
        return flt(capacity.day_shift_capacity_kg) + flt(capacity.night_shift_capacity_kg)
    return 0


def update_unit_capacity_usage(unit_name):
    """Update current queue weight and available capacity"""
    # Get all finalized sheets for this unit
    sheets = frappe.get_all("Planning Sheet",
                           filters={
                               "allocated_unit": unit_name,
                               "planning_status": ["in", ["Finalized", "In Production"]],
                               "docstatus": 1
                           },
                           fields=["total_weight"])
    
    total_queue_weight = sum([flt(sheet.total_weight) for sheet in sheets])
    
    # Update unit capacity
    unit_capacity = frappe.get_doc("Unit Capacity", unit_name)
    unit_capacity.current_queue_weight = total_queue_weight
    unit_capacity.queue_count = len(sheets)
    
    total_capacity = flt(unit_capacity.day_shift_capacity_kg) + flt(unit_capacity.night_shift_capacity_kg)
    unit_capacity.available_capacity = total_capacity - total_queue_weight
    unit_capacity.last_updated = now_datetime()
    
    unit_capacity.save(ignore_permissions=True)


# Scheduled Tasks

def daily_capacity_reset():
    """Reset capacity counters daily"""
    units = frappe.get_all("Unit Capacity", filters={"is_active": 1})
    
    for unit in units:
        update_unit_capacity_usage(unit.name)


def update_production_queue():
    """Update production queue hourly"""
    # Get all units
    units = frappe.get_all("Unit Capacity", filters={"is_active": 1}, pluck="name")
    
    for unit in units:
        # Get all sheets in production
        sheets = frappe.get_all("Planning Sheet",
                               filters={
                                   "allocated_unit": unit,
                                   "planning_status": "In Production",
                                   "docstatus": 1
                               },
                               fields=["name", "total_weight", "estimated_production_days"])
        
        # Check if any sheets are completed (logic can be enhanced)
        for sheet in sheets:
            # This is a placeholder - implement actual completion logic
            pass


# Whitelisted Methods

@frappe.whitelist()
def get_unit_queue_status(unit_name):
    """Get current queue status for a unit"""
    sheets = frappe.get_all("Planning Sheet",
                           filters={
                               "allocated_unit": unit_name,
                               "planning_status": ["in", ["Finalized", "In Production"]],
                               "docstatus": 1
                           },
                           fields=["name", "customer", "total_weight", "queue_position", 
                                  "delivery_date", "planning_status"],
                           order_by="queue_position asc")
    
    capacity = frappe.db.get_value("Unit Capacity", unit_name, 
                                   ["current_queue_weight", "available_capacity", 
                                    "day_shift_capacity_kg", "night_shift_capacity_kg"],
                                   as_dict=True)
    
    return {
        "sheets": sheets,
        "capacity": capacity
    }


@frappe.whitelist()
def get_quality_based_recommendation(quality, gsm):
    """Get unit recommendation based on quality and GSM"""
    UNIT_1 = ["SUPER PLATINUM", "PLATINUM", "PREMIUM", "GOLD", "SUPER CLASSIC"]
    UNIT_2 = ["GOLD", "SILVER", "BRONZE", "CLASSIC", "ECO SPECIAL", "ECO SPL"]
    UNIT_3 = ["SUPER PLATINUM", "PLATINUM", "PREMIUM", "GOLD", "SILVER", "BRONZE"]
    
    quality_upper = quality.upper() if quality else ""
    gsm_value = flt(gsm)
    
    recommended_unit = None
    
    if gsm_value > 50 and quality_upper in UNIT_1:
        recommended_unit = "Unit 1"
    elif gsm_value > 20 and quality_upper in UNIT_2:
        recommended_unit = "Unit 2"
    elif gsm_value > 10 and quality_upper in UNIT_3:
        recommended_unit = "Unit 3"
    elif gsm_value > 10:
        recommended_unit = "Unit 4"
    
    return recommended_unit


# Validation Hook
def validate_planning_sheet(doc, method):
    """Called from hooks on validate"""
    pass


# Unit Allocation Hook
def allocate_unit(doc, method):
    """Called from hooks before save"""
    pass


# Queue Update Hook
def update_queue(doc, method):
    """Called from hooks on submit"""
    pass
