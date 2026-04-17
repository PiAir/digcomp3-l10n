import os
import zipfile
import subprocess
import argparse
from datetime import datetime

def create_release(date_str=None):
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            print(f"Error: Invalid date format '{date_str}'. Use YYYYMMDD.")
            return
    else:
        target_date = datetime.now()
    
    date_yyyymmdd = target_date.strftime("%Y%m%d")
    date_iso = target_date.strftime("%Y-%m-%d")
    date_nl = f"{target_date.day}-{target_date.month}-{target_date.year}"
    
    output_dir = "output"
    zip_filename = f"release_{date_yyyymmdd}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    
    files_to_zip = [
        f"{date_yyyymmdd} - DigComp3.0-Nederlands_samengevoegd.pdf",
        f"{date_yyyymmdd} - DigComp_3.0_Data_Supplement_nl.xlsx",
        f"{date_yyyymmdd} - DigComp3.0-Nederlands_samengevoegd.docx"
    ]
    
    # Create ZIP
    print(f"Creating ZIP archive: {zip_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_zip:
            file_path = os.path.join(output_dir, file)
            if os.path.exists(file_path):
                print(f"Adding: {file}")
                zipf.write(file_path, arcname=file)
            else:
                print(f"Warning: File not found: {file_path}")
                # We still try to proceed if some files are missing, or should we abort?
                # User listed these 3 specific files.
    
    # Create GitHub Release
    release_name = f"DigComp 3.0 - beta {date_iso}"
    release_tag = f"beta-{date_iso}"
    release_desc = f"Betaversie van de Excel, JSON-D en PDF (nog zonder definitieve opmaak). Datum {date_nl}"
    
    print(f"Creating GitHub release: {release_name}")
    try:
        # Check if tag already exists and delete if necessary or just use a new one
        # For this task, we'll just create it. If it fails, we'll see the error.
        cmd = [
            "gh", "release", "create",
            release_tag,
            zip_path,
            "--title", release_name,
            "--notes", release_desc,
            "--confirm" # Use confirmed if possible or just run
        ]
        # Actually I can't use --confirm in non-interactive. Just run without it.
        # gh release create <tag> [<files>...] [flags]
        cmd = [
            "gh", "release", "create",
            release_tag,
            zip_path,
            "--title", release_name,
            "--notes", release_desc
        ]
        subprocess.run(cmd, check=True)
        print("Release created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error creating release: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a DigComp 3.0 release.")
    parser.add_argument("date", nargs="?", help="Date in YYYYMMDD format (default: today)")
    args = parser.parse_args()
    
    create_release(args.date)
