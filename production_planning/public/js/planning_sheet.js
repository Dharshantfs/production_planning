// Planning Sheet Client Script

frappe.ui.form.on('Planning Sheet', {
    refresh: function(frm) {
        // Add custom buttons
        if (frm.doc.docstatus === 1 && frm.doc.planning_status === "Finalized") {
            frm.add_custom_button(__('Start Production'), function() {
                frappe.call({
                    method: 'frappe.client.set_value',
                    args: {
                        doctype: 'Planning Sheet',
                        name: frm.doc.name,
                        fieldname: 'planning_status',
                        value: 'In Production'
                    },
                    callback: function(r) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __('Production Started'),
                            indicator: 'green'
                        });
                    }
                });
            });
        }
        
        if (frm.doc.allocated_unit) {
            frm.add_custom_button(__('View Queue Status'), function() {
                view_queue_status(frm);
            });
        }
        
        // Show unit recommendation
        if (!frm.doc.allocated_unit && frm.doc.items && frm.doc.items.length > 0) {
            frm.add_custom_button(__('Get Unit Recommendation'), function() {
                get_unit_recommendation(frm);
            });
        }
    },
    
    before_save: function(frm) {
        // Calculate totals before saving
        calculate_totals(frm);
    },
    
    sales_order: function(frm) {
        if (frm.doc.sales_order) {
            // Fetch sales order details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Sales Order',
                    name: frm.doc.sales_order
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('customer', r.message.customer);
                        frm.set_value('delivery_date', r.message.delivery_date);
                        
                        // Optionally populate items
                        if (r.message.items) {
                            frm.clear_table('items');
                            r.message.items.forEach(function(item) {
                                let row = frm.add_child('items');
                                row.item_code = item.item_code;
                                row.item_name = item.item_name;
                                row.qty = item.qty;
                                row.uom = item.uom;
                            });
                            frm.refresh_field('items');
                        }
                    }
                }
            });
        }
    }
});

frappe.ui.form.on('Planning Sheet Item', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.item_code) {
            // Parse item name to extract quality and color
            frappe.call({
                method: 'production_planning.production_planning.doctype.planning_sheet.planning_sheet.extract_quality_and_color',
                args: {
                    item_name: row.item_name
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'quality', r.message[0]);
                        frappe.model.set_value(cdt, cdn, 'color', r.message[1]);
                    }
                }
            });
        }
    },
    
    qty: function(frm, cdt, cdn) {
        calculate_item_weight(frm, cdt, cdn);
    },
    
    weight_per_roll: function(frm, cdt, cdn) {
        calculate_item_weight(frm, cdt, cdn);
    },
    
    no_of_rolls: function(frm, cdt, cdn) {
        calculate_item_weight(frm, cdt, cdn);
    },
    
    quality: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.quality && row.gsm) {
            get_item_unit_recommendation(frm, cdt, cdn);
        }
    },
    
    gsm: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.quality && row.gsm) {
            get_item_unit_recommendation(frm, cdt, cdn);
        }
        calculate_item_weight(frm, cdt, cdn);
    }
});

// Helper Functions

function calculate_item_weight(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (row.weight_per_roll && row.no_of_rolls) {
        let total_weight = flt(row.weight_per_roll) * flt(row.no_of_rolls);
        frappe.model.set_value(cdt, cdn, 'total_weight', total_weight);
    }
    
    // Recalculate form totals
    setTimeout(function() {
        calculate_totals(frm);
    }, 100);
}

function calculate_totals(frm) {
    let total_qty = 0;
    let total_weight = 0;
    
    frm.doc.items.forEach(function(item) {
        total_qty += flt(item.qty);
        total_weight += flt(item.total_weight);
    });
    
    frm.set_value('total_quantity', total_qty);
    frm.set_value('total_weight', total_weight);
    
    // Calculate estimated production days
    if (frm.doc.allocated_unit && total_weight > 0) {
        let day_capacity = flt(frm.doc.unit_capacity_day);
        let night_capacity = flt(frm.doc.unit_capacity_night);
        let total_capacity = day_capacity + night_capacity;
        
        if (total_capacity > 0) {
            let estimated_days = total_weight / total_capacity;
            frm.set_value('estimated_production_days', estimated_days);
        }
    }
}

function get_item_unit_recommendation(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    frappe.call({
        method: 'production_planning.production_planning.doctype.planning_sheet.planning_sheet.get_quality_based_recommendation',
        args: {
            quality: row.quality,
            gsm: row.gsm
        },
        callback: function(r) {
            if (r.message) {
                frappe.model.set_value(cdt, cdn, 'allocated_to_unit', r.message);
            }
        }
    });
}

function get_unit_recommendation(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.msgprint(__('Please add items first'));
        return;
    }
    
    // Collect quality and GSM data
    let quality_weights = {};
    let total_weight = 0;
    let avg_gsm = 0;
    
    frm.doc.items.forEach(function(item) {
        let weight = flt(item.total_weight) || flt(item.qty);
        let quality = (item.quality || '').toUpperCase();
        
        if (quality) {
            quality_weights[quality] = (quality_weights[quality] || 0) + weight;
        }
        
        total_weight += weight;
        avg_gsm += flt(item.gsm) * weight;
    });
    
    avg_gsm = total_weight > 0 ? avg_gsm / total_weight : 0;
    
    // Find dominant quality
    let dominant_quality = '';
    let max_weight = 0;
    
    for (let quality in quality_weights) {
        if (quality_weights[quality] > max_weight) {
            max_weight = quality_weights[quality];
            dominant_quality = quality;
        }
    }
    
    if (dominant_quality) {
        frappe.call({
            method: 'production_planning.production_planning.doctype.planning_sheet.planning_sheet.get_quality_based_recommendation',
            args: {
                quality: dominant_quality,
                gsm: avg_gsm
            },
            callback: function(r) {
                if (r.message) {
                    frappe.msgprint({
                        title: __('Unit Recommendation'),
                        message: __('Based on Quality: {0} and Average GSM: {1}<br>Recommended Unit: <b>{2}</b>', 
                                  [dominant_quality, avg_gsm.toFixed(2), r.message]),
                        primary_action: {
                            label: __('Apply'),
                            action: function() {
                                frm.set_value('allocated_unit', r.message);
                                frm.save();
                            }
                        }
                    });
                }
            }
        });
    }
}

function view_queue_status(frm) {
    if (!frm.doc.allocated_unit) {
        frappe.msgprint(__('No unit allocated yet'));
        return;
    }
    
    frappe.call({
        method: 'production_planning.production_planning.doctype.planning_sheet.planning_sheet.get_unit_queue_status',
        args: {
            unit_name: frm.doc.allocated_unit
        },
        callback: function(r) {
            if (r.message) {
                show_queue_dialog(frm.doc.allocated_unit, r.message);
            }
        }
    });
}

function show_queue_dialog(unit_name, data) {
    let sheets = data.sheets || [];
    let capacity = data.capacity || {};
    
    let html = `
        <div style="margin-bottom: 20px;">
            <h4>${unit_name} - Capacity Status</h4>
            <table class="table table-bordered" style="margin-top: 10px;">
                <tr>
                    <td><b>Day Shift Capacity:</b></td>
                    <td>${flt(capacity.day_shift_capacity_kg).toFixed(2)} KG</td>
                </tr>
                <tr>
                    <td><b>Night Shift Capacity:</b></td>
                    <td>${flt(capacity.night_shift_capacity_kg).toFixed(2)} KG</td>
                </tr>
                <tr>
                    <td><b>Current Queue Weight:</b></td>
                    <td>${flt(capacity.current_queue_weight).toFixed(2)} KG</td>
                </tr>
                <tr>
                    <td><b>Available Capacity:</b></td>
                    <td style="color: ${flt(capacity.available_capacity) > 0 ? 'green' : 'red'};">
                        ${flt(capacity.available_capacity).toFixed(2)} KG
                    </td>
                </tr>
            </table>
        </div>
        
        <h4>Current Queue (${sheets.length} orders)</h4>
        <table class="table table-bordered" style="margin-top: 10px;">
            <thead>
                <tr>
                    <th>Position</th>
                    <th>Planning Sheet</th>
                    <th>Customer</th>
                    <th>Weight (KG)</th>
                    <th>Delivery Date</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    sheets.forEach(function(sheet) {
        let status_color = sheet.planning_status === 'In Production' ? 'blue' : 'green';
        html += `
            <tr>
                <td>${sheet.queue_position || '-'}</td>
                <td><a href="/app/planning-sheet/${sheet.name}">${sheet.name}</a></td>
                <td>${sheet.customer || ''}</td>
                <td>${flt(sheet.total_weight).toFixed(2)}</td>
                <td>${frappe.datetime.str_to_user(sheet.delivery_date)}</td>
                <td><span style="color: ${status_color};">${sheet.planning_status}</span></td>
            </tr>
        `;
    });
    
    html += `
            </tbody>
        </table>
    `;
    
    frappe.msgprint({
        title: __('Queue Status - {0}', [unit_name]),
        message: html,
        wide: true
    });
}
