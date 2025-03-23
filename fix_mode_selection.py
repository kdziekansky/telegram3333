# Fix for mode selection handler
# Save this as fix_mode_selection.py and run it to patch the main.py file

def patch_main_py():
    """
    Patches the main.py file to fix the mode selection handler
    """
    # Read main.py
    with open('main.py', 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Find the line with mode selection handler registration
    old_line = "application.add_handler(CallbackQueryHandler(handle_mode_selection, pattern=\"^mode_\"))"
    
    # Check if the line exists
    if old_line not in content:
        print("Could not find the mode selection handler line in main.py")
        return False
    
    # Create a wrapper function that will extract the mode_id
    new_code = """
# Wrapper function for mode selection
async def handle_mode_callback(update, context):
    # Extracts mode_id and calls handle_mode_selection
    query = update.callback_query
    mode_id = query.data[5:]  # Extract mode_id from "mode_XXX"
    await handle_mode_selection(update, context, mode_id)

"""
    
    # Replace the handler registration
    new_line = "application.add_handler(CallbackQueryHandler(handle_mode_callback, pattern=\"^mode_\"))"
    
    # Insert the new code before the application handlers section
    insert_marker = "# Rejestracja handlerów komend"
    new_content = content.replace(insert_marker, new_code + insert_marker, 1)
    
    # Replace the handler registration line
    new_content = new_content.replace(old_line, new_line)
    
    # Write the updated content back to main.py
    with open('main.py', 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    print("Successfully patched main.py to fix mode selection")
    return True

# Run the patch
if __name__ == "__main__":
    patch_main_py()