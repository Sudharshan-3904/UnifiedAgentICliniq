# BMI Calculator MCP Server

This is a Model Context Protocol (MCP) server that provides a BMI (Body Mass Index) calculator tool, designed to be used as a backend for ChatGPT applications.

## Features

- Calculates BMI from height (in meters) and weight (in kilograms)
- Provides BMI category classification (Underweight, Normal, Overweight, Obese)
- Input validation for positive values
- Asynchronous tool execution

## Installation

1. Ensure you have Python 3.8 or higher installed.

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the MCP server:

   ```bash
   python bmi_mcp_server.py
   ```

2. Configure your ChatGPT app to connect to this MCP server. The server communicates via stdio, so you'll need to set up the appropriate integration in your ChatGPT app's MCP configuration.

3. The available tool is `calculate_bmi` which takes two parameters:
   - `height`: Height in meters (float)
   - `weight`: Weight in kilograms (float)

   Example usage in ChatGPT: "Calculate my BMI with height 1.75 and weight 70"

## Tool Details

- **Name**: calculate_bmi
- **Description**: Calculate Body Mass Index (BMI) from height and weight
- **Parameters**:
  - height (float): Height in meters
  - weight (float): Weight in kilograms
- **Returns**: String containing BMI value and category

## BMI Categories

- Underweight: BMI < 18.5
- Normal weight: 18.5 ≤ BMI < 25
- Overweight: 25 ≤ BMI < 30
- Obese: BMI ≥ 30

## Troubleshooting

- **Import errors**: Ensure the MCP SDK is properly installed with `pip install mcp`
- **Python version**: Requires Python 3.8+
- **Server not responding**: Check that the server is running and the stdio connection is properly configured in your ChatGPT app
- **Invalid inputs**: The tool validates that height and weight are positive numbers

## License

This project is provided as-is for educational and development purposes.
