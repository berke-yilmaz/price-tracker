# quick_fix_database.py - Run this script to fix the database immediately

import os
import sys
import django

# Add your project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PriceTracker.settings')
django.setup()

from django.db import connection

def fix_processingjob_field():
    """Directly alter the database to fix the job_type field length"""
    with connection.cursor() as cursor:
        try:
            # Check current column definition
            cursor.execute("""
                SELECT character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'api_processingjob' 
                AND column_name = 'job_type';
            """)
            
            result = cursor.fetchone()
            if result:
                current_length = result[0]
                print(f"Current job_type field length: {current_length}")
                
                if current_length < 50:
                    print("Updating job_type field to 50 characters...")
                    
                    # Alter the column
                    cursor.execute("""
                        ALTER TABLE api_processingjob 
                        ALTER COLUMN job_type TYPE VARCHAR(50);
                    """)
                    
                    print("✅ Successfully updated job_type field length to 50 characters")
                else:
                    print("✅ job_type field is already 50+ characters long")
            else:
                print("❌ Could not find api_processingjob table or job_type column")
                
        except Exception as e:
            print(f"❌ Error updating database: {e}")
            print("You may need to create and run a proper Django migration instead")

if __name__ == "__main__":
    fix_processingjob_field()