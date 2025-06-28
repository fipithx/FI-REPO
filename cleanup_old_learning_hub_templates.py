import os
import sys

def cleanup_old_templates():
    """Remove old Learning Hub template files that have been consolidated."""
    
    # Define the directory containing old templates
    templates_dir = "templates/LEARNINGHUB"
    
    # List of old template files to remove (excluding email template)
    old_templates = [
        "learning_hub_course_overview.html",
        "learning_hub_courses.html", 
        "learning_hub_dashboard.html",
        "learning_hub_lesson_completed.html",
        "learning_hub_lesson.html",
        "learning_hub_profile.html",
        "learning_hub_quiz.html",
        "learning_hub_upload.html"
    ]
    
    print("Starting cleanup of old Learning Hub templates...")
    
    # Check if templates directory exists
    if not os.path.exists(templates_dir):
        print(f"Directory {templates_dir} does not exist. Nothing to clean up.")
        return
    
    removed_count = 0
    
    # Remove each old template file
    for template_file in old_templates:
        file_path = os.path.join(templates_dir, template_file)
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Removed: {file_path}")
                removed_count += 1
            except OSError as e:
                print(f"Error removing {file_path}: {e}")
        else:
            print(f"File not found (already removed): {file_path}")
    
    print(f"\nCleanup completed. Removed {removed_count} old template files.")
    print("Note: learning_hub_lesson_completed_gmail.html was preserved as it's an email template.")

if __name__ == "__main__":
    cleanup_old_templates()