/*
===============================================================
ISHA CERTIFIED YOGA TRAINER DATA COLLECTION AUTOMATION
===============================================================

PURPOSE:
This script automatically clicks the "Load More" button on the
Isha Certified Hatha Yoga Teachers page until all available
trainer records are loaded.

After loading everything, it collects the visible page text and
downloads it as:

    Isha_Certified_Yoga_Trainers.txt


===============================================================
HOW TO USE THIS SCRIPT
===============================================================

1. Open the Isha Certified Yoga Teachers page in Google Chrome:

   https://isha.sadhguru.org/in/en/yoga-meditation/yoga-program-for-beginners/hatha-yoga/courses-by-certified-teachers


2. Open Chrome Developer Tools:

   Press F12


3. Go to:

   Sources → Snippets


4. Click:

   + New snippet


5. Paste this entire code into the snippet editor.


6. Press:

   Ctrl + Enter

   This starts the automation.


7. DO NOT close or refresh the page while the script is running.

   The script will automatically:

   - Scroll to the bottom
   - Find the "Load More" button
   - Click it
   - Wait for new records to load
   - Repeat the process
   - Stop when the Load More button is no longer available


8. When the process finishes, the script automatically creates:

   Isha_Certified_Yoga_Trainers.txt

   The file should normally appear in your Chrome Downloads folder.


===============================================================
IMPORTANT
===============================================================

Do NOT manually click the Load More button while this script
is running.

Do NOT refresh the page.

Do NOT close the browser tab.

The process may take several minutes if there are many batches
of trainers.


===============================================================
*/


/*
---------------------------------------------------------------
STEP 1: Start the asynchronous function
---------------------------------------------------------------

The entire automation is wrapped inside an async function so
that we can use "await" while waiting for the webpage to load.
*/

(async () => {

    /*
    Display a message in the DevTools Console so that the user
    knows that the automation has started.
    */

    console.log("🚀 Starting Isha Yoga Trainer collection...");


    /*
    -----------------------------------------------------------
    STEP 2: Create a waiting function
    -----------------------------------------------------------

    Websites need time to load new records after clicking
    "Load More".

    This function allows us to pause the script for a specific
    number of milliseconds.

    Example:

        await sleep(2500);

    means:

        Wait for 2.5 seconds.
    */

    const sleep = ms =>
        new Promise(resolve => setTimeout(resolve, ms));


    /*
    -----------------------------------------------------------
    STEP 3: Find the "Load More" button
    -----------------------------------------------------------

    The website may implement the Load More control as:

    - a <button>
    - an <a> link
    - an element with role="button"

    Therefore, the script checks all three possibilities.
    */

    function findLoadMore() {

        const elements = [

            ...document.querySelectorAll("button"),

            ...document.querySelectorAll("a"),

            ...document.querySelectorAll('[role="button"]')

        ];


        /*
        Search through all discovered elements and find one whose
        visible text is exactly "Load More".
        */

        return elements.find(el => {

            /*
            Get the text contained inside the element.
            */

            const text =
                (el.innerText || el.textContent || "")
                    .trim()
                    .replace(/\s+/g, " ")
                    .toLowerCase();


            /*
            Return the element only if:

            1. Its text is "load more"
            2. It is currently visible on the page
            */

            return text === "load more" &&
                   el.offsetParent !== null;

        });

    }


    /*
    -----------------------------------------------------------
    STEP 4: Create counters
    -----------------------------------------------------------
    */

    /*
    Number of times the Load More button has been clicked.
    */

    let clicks = 0;


    /*
    Counts how many consecutive times the script could not find
    a Load More button.

    We use three checks instead of immediately stopping because
    the webpage may temporarily be loading.
    */

    let noButtonCount = 0;


    /*
    -----------------------------------------------------------
    STEP 5: Start the automatic Load More process
    -----------------------------------------------------------

    The loop continues until the script determines that there
    are no more trainer records to load.
    */

    while (true) {


        /*
        Scroll to the bottom of the page.

        This helps bring the Load More button into view.
        */

        window.scrollTo({

            top: document.body.scrollHeight,

            behavior: "smooth"

        });


        /*
        Wait 1.2 seconds for the scrolling and page rendering.
        */

        await sleep(1200);


        /*
        Look for the Load More button.
        */

        const button = findLoadMore();


        /*
        -------------------------------------------------------
        CASE 1:
        Load More button was NOT found
        -------------------------------------------------------
        */

        if (!button) {

            /*
            Increase the number of unsuccessful checks.
            */

            noButtonCount++;


            /*
            Display the current status in the Console.
            */

            console.log(
                `No Load More button found. Check ${noButtonCount}/3`
            );


            /*
            If the button cannot be found three consecutive times,
            assume that all available records have been loaded.
            */

            if (noButtonCount >= 3) {

                break;

            }


            /*
            Give the page another 2 seconds before checking again.
            */

            await sleep(2000);

            continue;

        }


        /*
        -------------------------------------------------------
        CASE 2:
        Load More button WAS found
        -------------------------------------------------------

        Reset the unsuccessful-check counter.
        */

        noButtonCount = 0;


        /*
        Make sure the button is visible in the middle of the
        screen before clicking it.
        */

        button.scrollIntoView({

            behavior: "smooth",

            block: "center"

        });


        /*
        Wait half a second after scrolling.
        */

        await sleep(500);


        /*
        Click the Load More button.
        */

        button.click();


        /*
        Increase the click counter.
        */

        clicks++;


        /*
        Show progress in the Console.

        Example:

        ✅ Load More clicked: 1
        ✅ Load More clicked: 2
        ✅ Load More clicked: 3
        */

        console.log(
            `✅ Load More clicked: ${clicks}`
        );


        /*
        IMPORTANT:

        Wait 2.5 seconds after every click.

        This gives the website time to request and display the
        next batch of trainer records.
        */

        await sleep(2500);

    }


    /*
    -----------------------------------------------------------
    STEP 6: Loading is complete
    -----------------------------------------------------------
    */

    console.log("=================================");

    console.log(
        "🎉 ALL AVAILABLE TRAINERS LOADED"
    );

    console.log(
        `Total Load More clicks: ${clicks}`
    );

    console.log("=================================");


    /*
    -----------------------------------------------------------
    STEP 7: Final waiting period
    -----------------------------------------------------------

    Give the website an additional 3 seconds to finish rendering
    any content from the final Load More request.
    */

    await sleep(3000);


    /*
    -----------------------------------------------------------
    STEP 8: Collect the page text
    -----------------------------------------------------------

    document.body.innerText gets the text currently displayed
    on the webpage.

    Since all available trainer batches have now been loaded,
    this includes the information that was dynamically added
    to the page.
    */

    const pageText = document.body.innerText;


    /*
    -----------------------------------------------------------
    STEP 9: Prepare the output text
    -----------------------------------------------------------

    We create a formatted text document containing:

    - Title
    - Source URL
    - Number of Load More clicks
    - Complete page text
    */

    const output =
`ISHA CERTIFIED HATHA YOGA TEACHERS
====================================

SOURCE:
https://isha.sadhguru.org/in/en/yoga-meditation/yoga-program-for-beginners/hatha-yoga/courses-by-certified-teachers

TOTAL LOAD MORE CLICKS:
${clicks}

====================================
COMPLETE PAGE DATA
====================================

${pageText}
`;


    /*
    -----------------------------------------------------------
    STEP 10: Create a downloadable text file
    -----------------------------------------------------------

    Blob converts our collected text into a file-like object.
    */

    const blob = new Blob(

        [output],

        {
            type: "text/plain;charset=utf-8"
        }

    );


    /*
    Create a temporary URL for the generated file.
    */

    const url = URL.createObjectURL(blob);


    /*
    -----------------------------------------------------------
    STEP 11: Create the download link
    -----------------------------------------------------------
    */

    const download = document.createElement("a");


    /*
    Tell Chrome where the generated file is located.
    */

    download.href = url;


    /*
    Set the filename that Chrome should use.
    */

    download.download =
        "Isha_Certified_Yoga_Trainers.txt";


    /*
    Add the temporary download link to the webpage.
    */

    document.body.appendChild(download);


    /*
    Automatically click the download link.

    This starts the download without the user having to
    manually copy the entire page.
    */

    download.click();


    /*
    Remove the temporary link after the download has started.
    */

    download.remove();


    /*
    Release the temporary URL from memory.
    */

    URL.revokeObjectURL(url);


    /*
    -----------------------------------------------------------
    STEP 12: Show completion message
    -----------------------------------------------------------
    */

    console.log("📄 File downloaded:");

    console.log(
        "Isha_Certified_Yoga_Trainers.txt"
    );


/*
---------------------------------------------------------------
END OF AUTOMATION
---------------------------------------------------------------
*/

})();
