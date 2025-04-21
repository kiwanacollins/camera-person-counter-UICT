Redesign the UI of this applicationand add the following sections on the sidebar using the following information but dont tamper with the detection functionality beacuse it works 
Page 1: Live Camera Feed

Key Features:

Live Video Feed:

Include a counter overlay in the corner showing the total number of individuals currently detected.

Controls:

Add a "Pause/Resume" button to temporarily freeze the video feed.

Include a "Fullscreen" button for better visibility.

Design Considerations:

Ensure the video feed is centered and occupies most of the screen.

Page 2: Counter Dashboard
Description:
This page provides a real-time overview of the system's performance, including the total count of detected individuals and system status.

Key Features:

Real-Time Count Display:

Show the total number of individuals detected in large, bold text.

Update the count dynamically as the AI detects changes.

Status Indicators:

Use color-coded badges for system status:

Green: "Active" (system is functioning normally).

Red: "Error" (e.g., camera disconnected or no feed).

Yellow: "Warning" (e.g., low detection sensitivity).

Visual Trends:

Include a line chart or bar graph showing the count trend over the last 5-10 minutes.

Use a library like Chart.js or D3.js for the graph.

Refresh Button:

Add a button to manually refresh the count and status.

Design Considerations:

Use a clean, minimalist layout with a focus on the count and status.

Place the graph below the count for easy reference.

Page 3: System Configuration Page
Description:
This page allows users to customize system settings for optimal performance.

Key Features:

Camera Selection:

Dropdown menu to select from available cameras.

Include a "Test Camera" button to preview the selected feed.

Detection Sensitivity:

Slider to adjust sensitivity (e.g., low, medium, high).

Show a tooltip explaining the impact of each sensitivity level.

Logging Preferences:

Toggle to enable/disable logging.

Dropdown to select log frequency (e.g., every minute, every 5 minutes).

Save/Cancel Buttons:

"Save" button to apply changes.

"Cancel" button to revert to previous settings.

Design Considerations:

Use a form-like layout with clear labels and input fields.

Group related settings into sections (e.g., "Camera Settings," "Detection Settings").

Page 4: Logs and Reports Page
Description:
This page displays historical data in a tabular format for analysis and reporting.

Key Features:

Table Layout:

Columns: Timestamp, Count, Status.

Rows: Each detection event with its corresponding data.

Search and Filter:

Add a search bar to filter logs by timestamp or status.

Include date pickers to filter logs by a specific date range.

Export Options:

Buttons to export logs as CSV or PDF.

Pagination:

Display logs in pages (e.g., 10 logs per page) to avoid overwhelming the user.

Design Considerations:

Use a light theme for better readability of the table.

Highlight important rows (e.g., errors in red).

Page 5: Error Notifications
Description:
This page displays error messages and alerts users to potential system issues.

Key Features:

Error List:

Display a list of recent errors with timestamps.

Example errors: "Camera disconnected," "No individuals detected," "Low frame rate."

Error Details:

Clicking on an error should expand a section with more details (e.g., suggested actions, error code).

Clear Errors Button:

Add a button to clear resolved errors from the list.

Notification Badge:

Show a badge on the navigation menu indicating the number of active errors.

Design Considerations:

Use a red accent color for error messages to grab attention.

Ensure the error list is scrollable if there are many entries.

General Requirements for All Pages:
Navigation Menu:

Include a sidebar or top navigation bar with links to all pages.

Highlight the active page for better user orientation.

Responsive Design:

Ensure the interface works well on both desktop and mobile devices.

Styling:

Use a consistent color scheme and typography across all pages.

Add subtle animations (e.g., fade-in effects) for a polished look.

JavaScript Functionality:

Use JavaScript to handle dynamic updates (e.g., live feed, count, error notifications).

Use the local storage for storage of the necessary information

