function doPost(e) {
    var lock = LockService.getScriptLock();
    lock.tryLock(10000);

    try {
        var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
        var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
        var nextRow = sheet.getLastRow() + 1;

        // Parse the data sent from the HTML form
        var data = JSON.parse(e.postData.contents);
        var newRow = [];

        // Add Timestamp
        newRow.push(new Date());

        // Loop through headers (start at index 1 to skip Timestamp if you added it manually, 
        // but here we align with data keys)
        // Note: You must set up headers in Row 1 of your Sheet exactly matching these keys:
        // name, email, business_name, industry, employees, what_sell, typical_customer, 
        // source, top_tasks, magic_wand, leads_challenge, sales_team, closing_issues, 
        // delivery_time, ops_recurring, support_headaches, ai_experience, which_ai_tools, 
        // success_definition, specific_focus

        // Simplification: We will just map specific known keys to columns
        var fieldMapping = [
            "name", "email", "business_name", "industry", "employees",
            "what_sell", "typical_customer", "source",
            "top_tasks", "magic_wand",
            "leads_challenge",
            "sales_team", "closing_issues",
            "delivery_time", "ops_recurring",
            "support_headaches",
            "ai_experience", "which_ai_tools",
            "success_definition", "specific_focus"
        ];

        // If source is an array, join it
        if (Array.isArray(data.source)) {
            data.source = data.source.join(", ");
        }

        // Build the row
        for (var i = 0; i < fieldMapping.length; i++) {
            var key = fieldMapping[i];
            newRow.push(data[key] || "");
        }

        sheet.getRange(nextRow, 1, 1, newRow.length).setValues([newRow]);

        return ContentService
            .createTextOutput(JSON.stringify({ "result": "success", "row": nextRow }))
            .setMimeType(ContentService.MimeType.JSON);

    } catch (e) {
        return ContentService
            .createTextOutput(JSON.stringify({ "result": "error", "error": e }))
            .setMimeType(ContentService.MimeType.JSON);
    } finally {
        lock.releaseLock();
    }
}

function setup() {
    // Run this once to create headers
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var headers = [
        "Timestamp",
        "Name", "Email", "Business Name", "Industry", "Employees",
        "What You Sell", "Typical Customer", "Traffic Source",
        "Top 3 Tasks", "Magic Wand Task",
        "Leads Challenge",
        "Sales Team", "Closing Issues",
        "Delivery Time", "Recurring Ops Issues",
        "Support Headaches",
        "AI Experience", "Which AI Tools",
        "Success Definition", "Specific Focus"
    ];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
}
