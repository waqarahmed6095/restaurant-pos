Restaurant POS

Restaurant POS is a Windows desktop point-of-sale application for restaurants.
It is restaurant-agnostic: restaurant identity, branding, menu data, table
counts, and service-charge settings are entered when the application is first
installed.

## Features

- First-run restaurant setup
- Restaurant name, address, phone, email, logo, footer image, and separate Windows `.ico` app icon
- Menu import from JSON and menu management inside the application
- Configurable indoor and outdoor table counts
- Indoor, outdoor, and home-delivery orders
- Quantity controls and editable current orders
- Optional service charge
- Receipt and kitchen-slip previews
- ESC/POS printing when supported
- Automatic Windows printer discovery and spooler fallback
- Receipt-file fallback when no printer is available
- Session sales and date-filtered sales reports
- CSV sales-report export
- Staff PIN authentication and PIN changes
- Responsive, resizable windows

## Requirements

- Windows 10 or later
- Python 3.13 or later
- A Windows printer for physical printing

The application can also save receipt text files when a printer is unavailable.

## Development Setup

From the project directory:

```powershell
uv sync
.venv\Scripts\python.exe .\main.py
```

If the virtual environment already exists, the direct run command is:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

Run the test suite with:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_receipt
```

## First Launch

The first launch opens **Restaurant setup**. Enter:

- Restaurant name
- Address
- Phone number
- Optional email address
- Service charge
- Indoor table count
- Outdoor table count
- Logo image (`.png`, `.jpg`, or `.jpeg`)
- Footer image (`.png`, `.jpg`, or `.jpeg`)
- Separate Windows app icon (`.ico`)
- Optional menu JSON file

The form validates required fields, contact formats, numeric limits, image
paths, and menu-file contents before saving.

After setup, create the staff PIN. The PIN is required on later launches.

## Menu JSON Format

Menu files must contain a JSON array. Each item requires `category`, `name`,
`size`, and a non-negative numeric `price`:

```json
[
	{
		"category": "Pizza",
		"name": "Margherita Pizza",
		"size": "Medium",
		"price": 850
	},
	{
		"category": "Drinks",
		"name": "Cola",
		"size": "Regular",
		"price": 120
	}
]
```

Menu items can also be added, edited, or removed later through **Manage menu**.

## Daily Usage

1. Select a category, menu item, size, and quantity.
2. Add the item to the current order.
3. Select `Indoor`, `Outdoor`, or `Home Delivery`.
4. Select a table number when required.
5. Enable or disable the service charge.
6. Select **PRINT RECEIPT** to save the order and print the receipt and kitchen slip.

The application displays receipt and kitchen-slip previews before printing.

Use the session-sales and sales-report controls to review revenue. Sales
reports can be filtered by date and exported as CSV.

## Printing

On Windows, the application first attempts ESC/POS printing and uses the
Windows default printer. If ESC/POS is not compatible with the selected
printer, it falls back to the Windows printer spooler. If printing still fails,
receipt text is saved under the local `Output` directory.

The application detects local and connected Windows printers through
`pywin32`; no printer model is hard-coded.

## Local Data

Restaurant-specific data is stored outside the project and installed files:

```text
%APPDATA%\Restaurant POS\restaurant.json
%APPDATA%\Restaurant POS\menu_items.json
%APPDATA%\Restaurant POS\session_sales.json
%APPDATA%\Restaurant POS\access.pin
```

Receipt fallback files are written to the project or packaged application's
`Output` directory. These runtime files are excluded from Git by `.gitignore`.

## Build

Install the development dependencies and build the executable with PyInstaller:

```powershell
uv sync --dev
.\.venv\Scripts\pyinstaller.exe RoyaleBistro.spec
```

The executable is generated in `dist`. The Inno Setup script `rb.iss` can then
be used to create a Windows installer from the generated executable.

## Project Layout

```text
main.py                         Application entry point and UI
domain/                         Pricing and domain models
repositories/                   Menu, restaurant, and sales persistence
services/                       Receipt and kitchen-slip formatting
ui/                             Theme and UI styling
tests/                          Automated tests
RoyaleBistro.spec               PyInstaller build configuration
rb.iss                          Inno Setup installer configuration
pyproject.toml                  Python dependencies and project metadata
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for the
full license text.
