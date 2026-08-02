# Trustpilot scraper progress helper

START_PAGE = int(input("Enter start page: "))
END_PAGE = int(input("Enter end page: "))

PROGRESS_FILE='progress.txt'

def save_progress(page):
    with open(PROGRESS_FILE,'w') as f:
        f.write(f'Last Completed Page: {page}\n')
        f.write(f'Next Start Page: {page+1}\n')

print('Starting batch...')
for page in range(START_PAGE, END_PAGE+1):
    print(f'Scraping page {page}...')
    # Integrate your existing scrape functions here.
    save_progress(page)
    print(f'Completed page {page}')

print(f'Finished pages {START_PAGE}-{END_PAGE}')
print('Use output filename:')
print(f'trustpilot_pages_{START_PAGE}_to_{END_PAGE}.xlsx')
