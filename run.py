#!/usr/bin/env python3
"""
Enhanced CSV Processing Script for AI Company Data Crawler - REAL-TIME VERSION

Usage: python run.py <csv_file>
Example: python run.py test.csv

Features:
- Command line argument support
- Creates output folder automatically
- Separates success and failure results
- Custom filename schema with timestamps
- Real-time progress tracking and error handling
"""

import sys
import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import argparse
import time
from io import StringIO

def create_output_folder():
    """Create output folder if it doesn't exist"""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    return output_dir

def get_original_filename(file_path):
    """Extract original filename without extension"""
    return Path(file_path).stem

def generate_timestamp():
    """Generate timestamp in format YYYYMMDD_HHMMSS"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def split_results(processed_content, original_filename, timestamp):
    """Split processed results into success and failure files"""
    output_dir = create_output_folder()
    
    try:
        # Fix: Use io.StringIO instead of pd.io.StringIO
        df = pd.read_csv(StringIO(processed_content.decode('utf-8')))
        
        print(f"📊 Processing results: {len(df)} total companies")
        print(f"📋 Columns found: {list(df.columns)}")
        
        # Split into success and failure dataframes
        success_df = df[df['Status'] == 'Success'].copy()
        failure_df = df[df['Status'] != 'Success'].copy()
        
        print(f"✅ Success companies: {len(success_df)}")
        print(f"❌ Failed companies: {len(failure_df)}")
        
        # Generate filenames
        success_filename = f"{original_filename}-success-{timestamp}.csv"
        failure_filename = f"{original_filename}-failure-{timestamp}.csv"
        
        success_path = output_dir / success_filename
        failure_path = output_dir / failure_filename
        
        # Save files
        files_created = []
        
        if not success_df.empty:
            success_df.to_csv(success_path, index=False)
            files_created.append(success_path)
            print(f"💾 Success file created: {success_path} ({len(success_df)} companies)")
        else:
            print("⚠️  No successful results to save")
        
        if not failure_df.empty:
            failure_df.to_csv(failure_path, index=False)
            files_created.append(failure_path)
            print(f"💾 Failure file created: {failure_path} ({len(failure_df)} companies)")
        else:
            print("✅ No failures - all companies processed successfully!")
        
        return files_created, len(success_df), len(failure_df)
        
    except Exception as e:
        print(f"❌ Error splitting results: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        
        # Debug: Try to save raw content to see what we got
        debug_path = output_dir / f"{original_filename}-raw-debug-{timestamp}.txt"
        try:
            with open(debug_path, 'wb') as f:
                f.write(processed_content)
            print(f"🔍 Raw response saved for debugging: {debug_path}")
            print(f"   Response size: {len(processed_content)} bytes")
            print(f"   Response preview: {processed_content[:200].decode('utf-8', errors='ignore')}")
        except Exception as debug_error:
            print(f"   Could not save debug file: {debug_error}")
        
        # Fallback: save original file
        fallback_path = output_dir / f"{original_filename}-processed-{timestamp}.csv"
        try:
            with open(fallback_path, 'wb') as f:
                f.write(processed_content)
            print(f"💾 Fallback file saved: {fallback_path}")
            return [fallback_path], 0, 0
        except Exception as fallback_error:
            print(f"❌ Could not save fallback file: {fallback_error}")
            return [], 0, 0

def print_summary(original_filename, files_created, success_count, failure_count, processing_time):
    """Print processing summary"""
    total_count = success_count + failure_count
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    print("\n" + "="*60)
    print("📊 PROCESSING SUMMARY")
    print("="*60)
    print(f"Original file: {original_filename}")
    print(f"Total companies: {total_count}")
    print(f"Successful: {success_count} ({success_rate:.1f}%)")
    print(f"Failed: {failure_count} ({100-success_rate:.1f}%)")
    print(f"Processing time: {processing_time:.1f} seconds")
    print(f"Files created: {len(files_created)}")
    
    for file_path in files_created:
        print(f"  📁 {file_path}")
    
    print("="*60)

def process_companies_realtime(df, server_url, timeout, original_filename, timestamp):
    """Process companies one by one and print real-time status"""
    output_dir = create_output_folder()
    results = []
    total = len(df)
    company_col = 'Company Name' if 'Company Name' in df.columns else 'Company'
    website_col = None
    for col in ['Website', 'website', 'URL', 'url', 'Web Site', 'Company Website', 'WEBSITE']:
        if col in df.columns:
            website_col = col
            break

    # Mapping from API response keys to output columns
    api_to_output = {
        'company_name': 'Company Name',
        'website': 'Website',
        'phone_number': 'Phone Number',
        'street_address': 'Street Address',
        'city': 'City',
        'state': 'State',
        'zip_code': 'Zip Code',
        'facebook_page': 'Facebook Page',
        'facebook_page_name': 'Facebook Page Name',
        'facebook_likes': 'Facebook Likes',
        'facebook_about': 'Facebook About',
        'linkedin_page': 'LinkedIn Page',
        'public_email': 'Public Email',
        'contact_person': 'Contact Person',
        'processing_time': 'Processing Time (seconds)',
        'status': 'Status',
        'last_updated': 'Last Updated',
    }
    output_columns = list(api_to_output.values())

    print(f"\n=== REAL-TIME PROCESSING ({total} companies) ===")
    for idx, row in df.iterrows():
        company_name = str(row[company_col]).strip()
        website = str(row[website_col]).strip() if website_col and website_col in row and pd.notna(row[website_col]) else ''
        print(f"[{idx+1}/{total}] Processing: {company_name} ...", end=' ', flush=True)
        try:
            start_time = time.time()
            response = requests.post(
                f'{server_url}/process-single/',
                params={
                    'company_name': company_name,
                    'website': website
                },
                timeout=timeout or 300
            )
            elapsed = time.time() - start_time
            if response.status_code == 200:
                api_result = response.json()
                # Map API keys to output columns
                result = {col: '' for col in output_columns}
                for api_key, out_col in api_to_output.items():
                    if api_key in api_result:
                        result[out_col] = api_result[api_key]
                result['Processing Time (seconds)'] = elapsed
                results.append(result)
                print(f"✅ {result.get('Status', 'Success')} ({elapsed:.1f}s)")
            else:
                try:
                    error_info = response.json()
                    status = error_info.get('detail', 'Error')
                except Exception:
                    status = response.text[:100]
                result = {col: '' for col in output_columns}
                result['Company Name'] = company_name
                result['Website'] = website
                result['Status'] = f"Server error: {status}"
                result['Processing Time (seconds)'] = elapsed
                result['Last Updated'] = datetime.now().isoformat()
                results.append(result)
                print(f"❌ Server error: {status}")
        except requests.exceptions.Timeout:
            result = {col: '' for col in output_columns}
            result['Company Name'] = company_name
            result['Website'] = website
            result['Status'] = 'Timeout'
            result['Processing Time (seconds)'] = timeout or 300
            result['Last Updated'] = datetime.now().isoformat()
            results.append(result)
            print(f"❌ Timeout")
        except Exception as e:
            result = {col: '' for col in output_columns}
            result['Company Name'] = company_name
            result['Website'] = website
            result['Status'] = f"Error: {str(e)}"
            result['Processing Time (seconds)'] = 0
            result['Last Updated'] = datetime.now().isoformat()
            results.append(result)
            print(f"❌ Error: {str(e)}")
    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    # Fill missing columns for output compatibility
    for col in output_columns:
        if col not in results_df.columns:
            results_df[col] = ''
    results_df = results_df[output_columns]
    # Save as CSV (like split_results)
    success_df = results_df[results_df['Status'] == 'Success'].copy()
    failure_df = results_df[results_df['Status'] != 'Success'].copy()
    success_filename = f"{original_filename}-success-{timestamp}.csv"
    failure_filename = f"{original_filename}-failure-{timestamp}.csv"
    success_path = output_dir / success_filename
    failure_path = output_dir / failure_filename
    files_created = []
    if not success_df.empty:
        success_df.to_csv(success_path, index=False)
        files_created.append(success_path)
        print(f"\n💾 Success file created: {success_path} ({len(success_df)} companies)")
    else:
        print("\n⚠️  No successful results to save")
    if not failure_df.empty:
        failure_df.to_csv(failure_path, index=False)
        files_created.append(failure_path)
        print(f"💾 Failure file created: {failure_path} ({len(failure_df)} companies)")
    else:
        print("✅ No failures - all companies processed successfully!")
    return files_created, len(success_df), len(failure_df)

def main():
    """Main function - Simplified Working Version Based on debug_run.py"""
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description='Process CSV file with AI Company Data Crawler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py test.csv
  python run.py companies.csv
  python run.py data/healthcare_companies.csv

Output:
  Creates 'output' folder with separate success/failure CSV files
  Filename format: originalName-success-YYYYMMDD_HHMMSS.csv
        """
    )
    
    parser.add_argument('csv_file', help='Path to the CSV file to process')
    parser.add_argument('--server', default='http://localhost:8000', 
                       help='Crawler server URL (default: http://localhost:8000)')
    parser.add_argument('--timeout', type=int, default=None,
                       help='Request timeout in seconds (default: auto-calculated)')
    
    # Parse arguments
    args = parser.parse_args()
    
    print("🤖 AI Company Data Crawler - CSV Processor")
    print("="*50)
    
    # Step 1: Basic file validation (like debug script)
    print("=== FILE VALIDATION ===")
    if not os.path.exists(args.csv_file):
        print(f"❌ File not found: {args.csv_file}")
        sys.exit(1)
    
    if not args.csv_file.lower().endswith('.csv'):
        print(f"❌ File must be CSV: {args.csv_file}")
        sys.exit(1)
    
    print(f"✅ File exists: {args.csv_file}")
    
    # Step 2: CSV validation (like debug script)
    print("\n=== CSV VALIDATION ===")
    try:
        df = pd.read_csv(args.csv_file)
        required_columns = ['Company', 'Company Name']
        if not any(col in df.columns for col in required_columns):
            print(f"❌ CSV must contain 'Company' or 'Company Name' column")
            print(f"   Found: {list(df.columns)}")
            sys.exit(1)
        print(f"✅ CSV validated: {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        print(f"❌ CSV error: {e}")
        sys.exit(1)
    
    # Step 3: Server check (like debug script)
    print("\n=== SERVER CHECK ===")
    try:
        response = requests.get(f"{args.server}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"❌ Server error: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("💡 Make sure to run: python main.py")
        sys.exit(1)
    
    # Setup output
    original_filename = get_original_filename(args.csv_file)
    timestamp = generate_timestamp()
    
    print(f"\n📝 Original file: {original_filename}")
    print(f"🕐 Timestamp: {timestamp}")
    print(f"📂 Output folder: ./output/")
    print("-" * 50)
    
    # Step 4: Real-time Processing
    print("=== PROCESSING (REAL-TIME) ===")
    start_time = time.time()
    try:
        timeout = args.timeout
        if timeout is None:
            timeout = 180 + (len(df) * 45)
            timeout = max(600, min(3600, timeout))
        print(f"⏱️  Timeout: {timeout//60} minutes for {len(df)} companies")
        print("📤 Starting real-time processing...")
        files_created, success_count, failure_count = process_companies_realtime(
            df, args.server, timeout, original_filename, timestamp
        )
        processing_time = time.time() - start_time
        print_summary(original_filename, files_created, success_count, failure_count, processing_time)
        if success_count > 0:
            print("\n🎉 Processing completed successfully!")
        else:
            print("\n⚠️  Processing completed but no successful results.")
        return 0
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)