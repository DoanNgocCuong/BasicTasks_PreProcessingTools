import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime

def analyze_classification_results(file_path, bin_size=20):
    """
    Analyze classification results and create a histogram showing the distribution
    of children voices across bins of URLs.
    
    Args:
        file_path (str): Path to the classification_summary.txt file
        bin_size (int): Number of URLs per bin (default: 20)
    """
    
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Get statistics
    total_urls = len(df)
    child_mask = df['Result'] == 'Child'
    child_indices = df[child_mask].index.tolist()
    
    # Create bins based on original position in the file
    num_bins = (total_urls + bin_size - 1) // bin_size  # Ceiling division
    
    # Count children voices in each bin
    bin_counts = [0] * num_bins
    for child_idx in child_indices:
        bin_number = child_idx // bin_size
        if bin_number < num_bins:
            bin_counts[bin_number] += 1
    
    # Create bin labels
    bin_labels = [f"URLs {i * bin_size + 1}-{min((i + 1) * bin_size, total_urls)}" 
                  for i in range(num_bins)]
    
    # Calculate statistics
    total_child = len(child_indices)
    total_non_child = len(df[df['Result'] == 'Non-Child'])
    total_errors = len(df[df['Result'] == 'Error'])
    
    # Print statistics
    print("=== Classification Results Analysis ===")
    print(f"Total URLs processed: {total_urls}")
    print(f"Total Child voices found: {total_child}")
    print(f"Total Non-Child voices: {total_non_child}")
    print(f"Total Errors: {total_errors}")
    print(f"Bin size: {bin_size} URLs per bin")
    print(f"Number of bins: {num_bins}")
    print()
    
    # Print bin-wise statistics
    print("=== Bin-wise Child Voice Distribution ===")
    for i, count in enumerate(bin_counts):
        start = i * bin_size + 1
        end = min((i + 1) * bin_size, total_urls)
        percentage = (count / total_child) * 100 if total_child > 0 else 0
        print(f"Bin {i+1} (URLs {start}-{end}): {count} child voices ({percentage:.1f}% of all child voices)")
    
    # Create and customize histogram
    plt.figure(figsize=(12, 6))
    bars = plt.bar(range(num_bins), bin_counts, alpha=0.7, color='skyblue', edgecolor='navy')
    
    # Highlight the bin with most child voices
    max_bin_idx = np.argmax(bin_counts)
    bars[max_bin_idx].set_color('orange')
    bars[max_bin_idx].set_edgecolor('red')
    
    # Customize plot
    plt.xlabel('URL Bins')
    plt.ylabel('Number of Child Voices')
    plt.title(f'Distribution of Child Voices Across URL Bins (Bin Size: {bin_size})')
    plt.xticks(range(num_bins), [f"Bin {i+1}" for i in range(num_bins)], rotation=45)
    plt.grid(axis='y', alpha=0.3)
    
    # Add value labels on top of bars
    for i, count in enumerate(bin_counts):
        plt.text(i, count + 0.1, str(count), ha='center', va='bottom')
    
    plt.tight_layout()
    
    # Save and display plot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(file_path).parent / f"child_voices_distribution_{timestamp}.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    
    max_count = bin_counts[max_bin_idx]
    print(f"\nBin with most child voices: Bin {max_bin_idx + 1} with {max_count} child voices")
    print(f"Histogram saved as: {output_path}")
    
    plt.show()
    
    return bin_counts, bin_labels

def save_analysis_summary(file_path, bin_counts, bin_labels, bin_size):
    """Save a summary of the analysis results to a timestamped text file."""
    input_path = Path(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = input_path.parent / f"analysis_summary_{timestamp}.txt"
    
    # Read data for statistics
    df = pd.read_csv(file_path)
    stats = {
        'total_urls': len(df),
        'total_child': len(df[df['Result'] == 'Child']),
        'total_non_child': len(df[df['Result'] == 'Non-Child']),
        'total_errors': len(df[df['Result'] == 'Error'])
    }
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write("Classification Results Analysis Summary\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Source file: {input_path.name}\n")
        f.write(f"Bin size: {bin_size}\n")
        f.write("=" * 50 + "\n\n")
        
        # Write overall statistics
        f.write(f"Total URLs processed: {stats['total_urls']}\n")
        f.write(f"Total Child voices found: {stats['total_child']}\n")
        f.write(f"Total Non-Child voices: {stats['total_non_child']}\n")
        f.write(f"Total Errors: {stats['total_errors']}\n\n")
        
        # Write bin-wise distribution
        f.write("Bin-wise Child Voice Distribution:\n")
        for i, count in enumerate(bin_counts):
            start = i * bin_size + 1
            end = min((i + 1) * bin_size, stats['total_urls'])
            percentage = (count / stats['total_child']) * 100 if stats['total_child'] > 0 else 0
            f.write(f"Bin {i+1} (URLs {start}-{end}): {count} child voices ({percentage:.1f}%)\n")
        
        # Write best bin info
        max_bin_idx = np.argmax(bin_counts)
        max_count = bin_counts[max_bin_idx]
        f.write(f"\nBin with most child voices: Bin {max_bin_idx + 1} with {max_count} child voices\n")
    
    print(f"Analysis summary saved as: {summary_path}")
    return summary_path

def find_classification_file(results_folder):
    """Find and return the most appropriate classification summary file."""
    base_filename = "classification_summary.txt"
    file_path = results_folder / base_filename
    
    if file_path.exists():
        print(f"Found file: {file_path.name}")
        return file_path
    
    # Look for timestamped versions
    pattern = "classification_summary_*.txt"
    matching_files = list(results_folder.glob(pattern))
    
    if matching_files:
        # Use the most recent file
        file_path = max(matching_files, key=lambda x: x.stat().st_mtime)
        print(f"Found timestamped file: {file_path.name}")
        return file_path
    
    # No files found
    print(f"Error: No classification summary files found in '{results_folder}'!")
    print("Looking for files matching patterns:")
    print(f"  - {base_filename}")
    print(f"  - classification_summary_YYYYMMDD_HHMMSS.txt")
    return None

def main():
    """Main function to orchestrate the classification analysis."""
    results_folder = Path("classification-results")
    
    # Check if folder exists
    if not results_folder.exists():
        print(f"Error: Folder '{results_folder}' not found!")
        print("Please make sure the classification-results folder exists and contains the classification_summary.txt file.")
        return
    
    # Find appropriate file
    file_path = find_classification_file(results_folder)
    if not file_path:
        return
    
    # Display file info
    print(f"Processing file: {file_path}")
    print(f"File created: {datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Analyze with default bin size of 20
    print("Analyzing with default bin size (20)...")
    bin_counts, bin_labels = analyze_classification_results(str(file_path), bin_size=20)
    
    # Save analysis summary with timestamp
    save_analysis_summary(str(file_path), bin_counts, bin_labels, 20)
    
    # Optional: Try different bin sizes for comparison
    print("\n" + "=" * 50)
    print("Analysis with different bin sizes:")
    
    for bin_size in [10, 15, 25, 30]:
        print(f"\n--- Bin size: {bin_size} ---")
        counts, _ = analyze_classification_results(str(file_path), bin_size)
        max_idx = np.argmax(counts)
        print(f"Bin with most child voices: Bin {max_idx + 1} with {counts[max_idx]} child voices")

if __name__ == "__main__":
    main()