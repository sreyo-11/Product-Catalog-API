import pandas as pd
from typing import List, Dict, Any
from app.schemas import ProductCreate
from pydantic import ValidationError


class CSVValidator:
    #Validates CSV file and individual product rows
    
    REQUIRED_FIELDS = ['sku', 'name', 'brand', 'color', 'size','mrp', 'price', 'quantity']
    
    @staticmethod
    def validate_csv_structure(df: pd.DataFrame) -> tuple[bool, str]:
        #Validate CSV has required columns
        missing_cols = set(CSVValidator.REQUIRED_FIELDS) - set(df.columns)
        if missing_cols:
            return False, f"Missing required columns: {', '.join(missing_cols)}"
        return True, "CSV structure is valid"
    
    @staticmethod
    def validate_row(row_data: Dict[str, Any], row_number: int) -> tuple[bool, ProductCreate | None, str]:
        #Validate individual product row
        try:
            # Check for missing required fields
            for field in CSVValidator.REQUIRED_FIELDS:
                if pd.isna(row_data.get(field)) or str(row_data.get(field)).strip() == '':
                    return False, None, f"Row {row_number}: Missing required field '{field}'"
            
            # Convert numeric fields
            try:
                row_data['mrp'] = float(row_data['mrp'])
                row_data['price'] = float(row_data['price'])
                row_data['quantity'] = int(row_data['quantity'])
            except (ValueError, TypeError) as e:
                return False, None, f"Row {row_number}: Invalid numeric value - {str(e)}"
            
            # Check quantity >= 0
            if row_data['quantity'] < 0:
                return False, None, f"Row {row_number}: quantity must be >= 0"
            
            # Check price <= mrp
            if row_data['price'] > row_data['mrp']:
                return False, None, f"Row {row_number}: price ({row_data['price']}) must be <= mrp ({row_data['mrp']})"
            
            # Create Pydantic model for validation
            product = ProductCreate(**row_data)
            return True, product, ""
            
        except ValidationError as e:
            error_msg = '; '.join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            return False, None, f"Row {row_number}: {error_msg}"
        except Exception as e:
            return False, None, f"Row {row_number}: Unexpected error - {str(e)}"
