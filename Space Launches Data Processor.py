##
#
# Space Launches Data Processor
# Copyright (C) 2023 Benedykt Synakiewicz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
##

##
##
## The imports.
##
##

# Standard packages.

from argparse import ArgumentParser
import csv
from datetime import datetime
from io import BytesIO
from pathlib import Path
import requests

# Third-party packages.

from bs4 import BeautifulSoup  # bs4
import dateparser  # dateparser
import matplotlib as mpl  # matplotlib
from matplotlib.colors import hsv_to_rgb, to_hex  # matplotlib
import matplotlib.pyplot as plt  # matplotlib
from matplotlib.ticker import MultipleLocator  # matplotlib
from PIL import Image, ImageColor  # pillow
from rich.console import Console  # rich

##
##
## The tiniest of utilities. Used in initializing some global constants, so have to be defined beforehand.
##
##

def GetColor(shadeDegrees: int, *, saturation: float = 0.7, value: float = 0.7) -> str:
    return to_hex(hsv_to_rgb((shadeDegrees / 360, saturation, value)))

##
##
## The global constants.
##
##

APPLICATION_NAME = "Space Launches Data Processor"
APPLICATION_CREATOR = "Ben Synakiewicz"

YEAR_MINIMUM = 1957  # The launch of Sputnik.
YEAR_MAXIMUM = datetime.now().year - 1 # The previous year. Since the current year is by definition incomplete, it would look
                                       # like a sudden drop at the end of every plot, which would be weird.

OUTPUT_DATA_PATH = Path("Data.csv")

DATABASE_URL = "https://space.skyrocket.de/"
DATABASE_URL_TEMPLATE = f"{DATABASE_URL}doc_chr/lauXXXX.htm"
HTML_PARSER_NAME = "html.parser"

COUNTRY_SITES = {
    "Brazil": ["Al"],
    "China": ["ECS", "Jq", "Xi", "TY", "We", "YS"],
    "Europe": ["Ha", "Ko", "Wo"],
    "India": ["Sr"],
    "Iran": ["Sem", "Shr"],
    "Israel": ["Pa"],
    "Japan": ["KA", "Ka", "Ta"],
    "North Korea": ["So", "To"],
    "South Korea": ["Na"],
    "USA": ["BC", "CC", "CCK", "Ed", "Ga", "In", "Kau", "Kd", "Kw", "Mo", "Nq", "Om", "OnS", "SLC", "SM", "Va", "WI"],
    "USSR/Russia": ["Ba", "BaS", "Do", "KY", "Pl", "SL", "Sv", "Vo"],
}

COLORS = {
    "Brazil": GetColor(131),
    "China": GetColor(50),
    "Europe": GetColor(188, saturation = 0.8),
    "India": GetColor(40, value = 0.9),
    "Iran": GetColor(131, value = 0.5),
    "Israel": GetColor(220, saturation = 0.1, value = 0.9),
    "Japan": GetColor(313, value = 0.9),
    "North Korea": GetColor(25),
    "South Korea": GetColor(0, saturation = 0.3),
    "USA": GetColor(219),
    "USSR/Russia": GetColor(5),

    "Success": GetColor(131),
    "Failure": GetColor(0, saturation = 0.0, value = 1.0),
    "Foreground": "#fff",
    "Annotation": "#bbb",
    "Decoration": "#777",
    "Background": "#31424c00",
}

ROCKET_FAMILIES = ["R-7", "Kosmos", "Proton", "Long March", "Atlas", "Falcon", "Ariane"]  # The order is visible in plots.
COLORS |= {
    "Ariane": COLORS["Europe"],
    "Atlas": GetColor(209),
    "Falcon": GetColor(259, saturation = 0.3, value = 1.0),
    "Kosmos": GetColor(15, saturation = 0.3),
    "Long March": COLORS["China"],
    "Proton": GetColor(35, saturation = 0.9, value = 0.5),
    "R-7": GetColor(5),
}

DPI = 300

SPACING_IN = 0.5  # "_IN" stands for inches.
SPACING_PX = int(SPACING_IN * DPI)  # "_PX" stands for pixels.

PLOT_SIZE_LONG = (
    18.0,
    4.0
)

PLOT_SIZE_SIDE = (
    PLOT_SIZE_LONG[0] / 2,
    PLOT_SIZE_LONG[1]
)

IMAGE_WIDTH_IN = PLOT_SIZE_LONG[0] + SPACING_IN + PLOT_SIZE_SIDE[0]

TINY_PLOT_COUNT = 7  # The number of tiny plots in a row.
PLOT_SIZE_TINY = (
    (IMAGE_WIDTH_IN - (TINY_PLOT_COUNT - 1) * SPACING_IN) / TINY_PLOT_COUNT,
    PLOT_SIZE_LONG[1] / 2,
)

PLOT_SIZE_EXTRA_LONG = (
    IMAGE_WIDTH_IN,
    PLOT_SIZE_LONG[1]
)

IMAGE_HEIGHT_IN = PLOT_SIZE_LONG[1] + PLOT_SIZE_TINY[1] + PLOT_SIZE_EXTRA_LONG[1] + PLOT_SIZE_TINY[1] + (3 + 1) * SPACING_IN

IMAGE_WIDTH_PX = int(IMAGE_WIDTH_IN * DPI)
IMAGE_HEIGHT_PX = int(IMAGE_HEIGHT_IN * DPI)

##
##
## The global variables
##
##

# The currently used language. It exists so that the language doesn't have to be manually passed in arguments to the translation
# function.
CurrentLanguage = ""

##
##
## The functions.
##
##


def DownloadTagSoup(URL: str) -> BeautifulSoup:

    response = requests.get(URL, timeout = 5)
    if response.status_code != 200:
        console.log(f'Invalid response status code: {response.status_code}. URL: "{URL}".')
        exit()

    return BeautifulSoup(response.text, features = HTML_PARSER_NAME)


def GetFileName(countryName: str) -> str:

    return countryName.split("/")[0]


def Translated(string: str) -> str:

    if CurrentLanguage == "en":
        return string

    dictionary = {
        "pl": {
            "Brazil": "Brazylia",
            "China": "Chiny",
            "Europe": "Europa",
            "India": "Indie",
            "Israel": "Izrael",
            "Japan": "Japonia",
            "North Korea": "Korea Północna",
            "South Korea": "Korea Południowa",
            "USSR/Russia": "ZSRR/Rosja",
            "Long March": "Długi Marsz",
            "Launches": "Starty",
            "All Successful Orbital Launches": "Wszystkie udane starty orbitalne",
            "Successful Launches": "Udane starty",
            "Total or Partial Failures": "Całkowite i częściowe porażki",
            "Successes and Failures": "Sukcesy i porażki",
            "Launches of Selected Rocket Families": "Starty wybranych rodzin rakiet",
            "↓ This line marks a hundred launches per year.": "↓ Ta linie określa granicę stu startów rocznie.",
            "← This line marks the end of the Cold War.": "← Ta linia wskazuje koniec zimnej wojny.",
        }
    }

    if CurrentLanguage in dictionary and string in dictionary[CurrentLanguage]:
        return dictionary[CurrentLanguage][string]

    return string

##
##
## The classes.
##
##

class Launch:

    def __init__(
        self: "Launch",
        date: str,
        vehicle: str,
        site: str,
        remarks: str,
        *,
        useFuzzyDateDecoding: bool = True
    ) -> None:

        # Process the arguments.

        date = date.strip()
        vehicle = vehicle.strip()
        site = site.strip()
        remarks = remarks.strip()

        # Initialize the parameters.

        self.Year = (dateparser.parse(date).date().year if useFuzzyDateDecoding else int(date[:4]))  # Fuzzy decoding is slow.
        self.Site = site.replace(",", " ")  # This way deducing the country is a bit more convenient.
        self.Country = ""
        self.Vehicle = " ".join(vehicle.split())  # Sometimes the whitespace in vehicle names is weird.
        self.Family = ""
        self.Remarks = remarks.lower()

        # Deduce the vehicle family.

        R7_SUBFAMILY_NAMES = ["Molniya", "Soyuz", "Sputnik", "Voskhod", "Vostok"]
        FAMILY_NAMES = ROCKET_FAMILIES + R7_SUBFAMILY_NAMES + ["CZ"] # "CZ" for the Long March.

        try:
            self.Family = next(n for n in FAMILY_NAMES if n in self.Vehicle)
        except StopIteration:
            pass

        if "CZ" == self.Family:
            self.Family = "Long March"
        elif self.Family in R7_SUBFAMILY_NAMES:
            self.Family = "R-7"

        # Deduce the success of the launch.

        self.Success = ("failure" not in self.Remarks) and ("failed" not in self.Remarks)

        # For whatever reason the initial launches of Falcon 1 aren't described as failed in the Remarks.
        if "Falcon-1 (dev)" in self.Vehicle:
            self.Success = False

        # Make corrections to the launch site description (in some very specific cases).

        if self.Site.startswith("@"):
            self.Site = self.Site[1:]

        self.Site = self.Site.replace("LC-1/5", "Ba LC-1/5")
        self.Site = self.Site.replace("SLC-", "SLC ")
        self.Site = self.Site.replace("YS(", "YS (")

        # Deduce the country.

        try:
            self.Country = next(country for country, prefixes in COUNTRY_SITES.items() if self.Site.split()[0] in prefixes)
        except StopIteration:
            pass

    def GetHeaderCSVRow(self: "Launch") -> str:

        return ";".join(f'"{x}"' for x in self.__dict__.keys())

    def GetCSVRow(self: "Launch") -> str:

        return ";".join(f'"{x}"' for x in self.__dict__.values())

##
##
## The executable code.
##
##

# Create the console and welcome the user.

console = Console()
console.print(f"[bold]{APPLICATION_NAME}, by {APPLICATION_CREATOR}.[/bold]")

# Process the command-line arguments.

argumentParser = ArgumentParser()
argumentParser.add_argument("Languages")

arguments = argumentParser.parse_args()
arguments.Languages = arguments.Languages.split(",")

# If no data is present locally, download it.

years = range(YEAR_MINIMUM, YEAR_MAXIMUM + 1)
launches = []

if not OUTPUT_DATA_PATH.is_file():

    # Download the data.

    console.print()
    console.print(f"[bold]Downloading the data from {DATABASE_URL}...[/bold]")

    for year in years:

        soup = DownloadTagSoup(DATABASE_URL_TEMPLATE.replace("XXXX", str(year)))

        for row in soup.select("table#chronlist tr"):

            cells = row.select("td")
            if len(cells) < 6:
                continue

            date = cells[1].get_text().strip()
            if "x" in date:
                continue

            launches.append(Launch(date, cells[3].get_text(), cells[4].get_text(), cells[5].get_text()))

        console.print(f"\rDownloaded data for the year {year}.", end = "\r")

    console.print()  # An empty line, since the lines printed in the loop lack a new line character at the end.
    console.print("The data has been downloaded.")

    # Export the data.

    console.print()
    console.print("[bold]Exporting the data...[/bold]")

    with open(OUTPUT_DATA_PATH, mode = "w", encoding = "UTF-8") as file:
        file.write(launches[0].GetHeaderCSVRow() + "\n" + "\n".join(x.GetCSVRow() for x in launches))

    console.print(f'The data has been exported to the output file: "{OUTPUT_DATA_PATH}".')

else:

    # Load the data.

    console.print()
    console.print(f'[bold]Loading the data from "{OUTPUT_DATA_PATH}"...[/bold]')

    with open(OUTPUT_DATA_PATH, encoding = "UTF-8") as file:

        reader = csv.reader(file, delimiter = ";")
        next(reader)  # Skip the header row.

        for row in reader:
            launches.append(Launch(row[0], row[3], row[1], row[5], useFuzzyDateDecoding = False))

    console.print(f"The data about {len(launches)} launches has been loaded.")

# Configure "matplotlib".

mpl.rcParams["font.family"] = "Source Sans Pro, sans-serif"
mpl.rcParams["font.size"] = "12.0"
mpl.rcParams["text.color"] = COLORS["Foreground"]

mpl.rcParams["axes.facecolor"] = COLORS["Background"]
mpl.rcParams["axes.edgecolor"] = mpl.rcParams["text.color"]
mpl.rcParams["axes.titlelocation"] = "left"
mpl.rcParams["axes.titlesize"] = "20.0"
mpl.rcParams["axes.titleweight"] = "600"
mpl.rcParams["axes.titlepad"] = mpl.rcParams["font.size"]
mpl.rcParams["axes.labelpad"] = mpl.rcParams["axes.titlepad"]
mpl.rcParams["axes.labelweight"] = mpl.rcParams["axes.titleweight"]
mpl.rcParams["axes.labelcolor"] = mpl.rcParams["text.color"]
mpl.rcParams["axes.spines.right"] = "False"
mpl.rcParams["axes.spines.top"] = "False"

mpl.rcParams["xtick.major.size"] = mpl.rcParams["ytick.major.size"] = mpl.rcParams["font.size"]
mpl.rcParams["xtick.color"] = mpl.rcParams["ytick.color"] = mpl.rcParams["text.color"]

mpl.rcParams["legend.frameon"] = "False"

mpl.rcParams["figure.figsize"] = ", ".join(str(x) for x in PLOT_SIZE_LONG)
mpl.rcParams["figure.dpi"] = DPI
mpl.rcParams["figure.facecolor"] = mpl.rcParams["axes.facecolor"] = COLORS["Background"]
mpl.rcParams["figure.constrained_layout.use"] = "True"

# Generate the plots.

for language in arguments.Languages:

    # Set the language as the current one.

    CurrentLanguage = language

    # Calculate some repeatedly used parameters.

    # The highest number of launches observed in any year.
    launchCountUpperRange = max([sum(x.Year == year for x in launches) for year in years])

    # Countries sorted by their total number of successful launches.
    countries = [ (c, sum(ln.Country == c and ln.Success for ln in launches)) for c in COUNTRY_SITES.keys()]
    countries.sort(key = lambda x: x[1], reverse = True)
    countries = [c for c, _ in countries]

    # Launches grouped by years.
    launchesByYear = {y: [ln for ln in launches if ln.Year == y] for y in years}
    successfulLaunchesByYear = {y: [ln for ln in launchesByYear[y] if ln.Success] for y in years}
    failedLaunchesByYear = {y: [ln for ln in launchesByYear[y] if not ln.Success] for y in years}

    # Create the "All Successful Orbital Launches" plot.

    console.print()
    console.print(f'[bold]\[{CurrentLanguage}] Generating the "All Successful Orbital Launches" plot...[/bold]')

    data = {c: {y: sum(ln.Success and ln.Country == c for ln in launchesByYear[y]) for y in years} for c in countries}
    totalSums = {c: sum(data[c].values()) for c in countries}  # Total number of successful launches for each country.

    figure, axes = plt.subplots()
    currentBottom = [0] * len(years)

    for index, country in enumerate(countries):

        label = f"{Translated(country)} ({totalSums[country]})"
        bars = axes.bar(years, data[country].values(), label = label, bottom = currentBottom, color = COLORS[country])

        currentBottom = [x + y for x, y in zip(currentBottom, data[country].values(), strict = True)]

        if index == len(countries) - 1:  # The uppermost country bar gets a label over it, with the total yearly launch count.
            axes.bar_label(bars, fmt = "%d", color = COLORS["Annotation"], fontsize = 8.0, padding = 3)

    axes.set_title(Translated("All Successful Orbital Launches"))
    axes.xaxis.set_major_locator(MultipleLocator(10))
    axes.set_ylabel(Translated("Launches"))
    axes.set_ylim([0, launchCountUpperRange])
    axes.legend(ncol = 6)

    LINE_ARGUMENTS = {"color": COLORS["Decoration"], "linestyle": ":", "linewidth": 1.6, "zorder": 0.0}
    LINE_TEXT_ARGUMENTS = {"color": COLORS["Annotation"], "fontsize": 12.0}

    H_LINE_TEXT_OFFSET = 5
    H_LINE_TEXT_POSITION = 2005
    H_LINE_TEXT_ARGUMENTS = LINE_TEXT_ARGUMENTS | {"va": "bottom", "ha": "center"}
    H_LINE_TEXT = Translated("↓ This line marks a hundred launches per year.")

    V_LINE_TEXT_OFFSET = 0.5
    V_LINE_TEXT_POSITION = 0.7 * launchCountUpperRange
    V_LINE_TEXT_ARGUMENTS = LINE_TEXT_ARGUMENTS | {"va": "center", "ha": "left"}
    V_LINE_TEXT = Translated("← This line marks the end of the Cold War.")

    plt.axhline(y = 100, **LINE_ARGUMENTS)
    plt.text(H_LINE_TEXT_POSITION, 100 + H_LINE_TEXT_OFFSET, H_LINE_TEXT, **H_LINE_TEXT_ARGUMENTS)

    plt.axvline(x = 1991, **LINE_ARGUMENTS)
    plt.text(1991 + V_LINE_TEXT_OFFSET, V_LINE_TEXT_POSITION, V_LINE_TEXT, **V_LINE_TEXT_ARGUMENTS)

    allLaunchesPlotBuffer = BytesIO()
    plt.savefig(allLaunchesPlotBuffer, format = "png")
    plt.close()
    allLaunchesPlotBuffer.seek(0)

    console.print("Plot generated.")

    # Create the "Successes and Failures" plot.

    console.print()
    console.print(f'[bold]\[{CurrentLanguage}] Generating the "Successes and Failures" plot...[/bold]')

    data = [(len(successfulLaunchesByYear[y]), len(failedLaunchesByYear[y])) for y in years]

    figure, axes = plt.subplots(figsize = PLOT_SIZE_SIDE)

    successLabel = f"{Translated('Successful Launches')} ({sum(s for s, _ in data)})"
    axes.bar(years, [s for s, _ in data], label = successLabel, color = COLORS["Success"])

    failureLabel = (f"{Translated('Total or Partial Failures')} ({sum(f for _, f in data)})")
    axes.bar(years, [f for _, f in data], label = failureLabel, color = COLORS["Failure"], bottom = [s for s, _ in data])

    axes.set_title(Translated("Successes and Failures"))
    axes.xaxis.set_major_locator(MultipleLocator(10))
    axes.set_ylim([0, launchCountUpperRange])
    axes.legend(ncol = 1)

    axes.get_yaxis().set_visible(False)
    axes.spines["left"].set_visible(False)

    plt.axhline(y = 100, **LINE_ARGUMENTS)  # Same lines as in the All Launches plot.
    plt.axvline(x = 1991, **LINE_ARGUMENTS)

    successesFailuresPlotBuffer = BytesIO()
    plt.savefig(successesFailuresPlotBuffer, format = "png")
    plt.close()
    successesFailuresPlotBuffer.seek(0)

    console.print("Plot generated.")

    # Create the "Country" plots.

    console.print()
    console.print(f'[bold]\[{CurrentLanguage}] Generating the "Country" plots for individual countries...[/bold]')

    countries = countries[:TINY_PLOT_COUNT]
    launchCountUpperRange = None

    countryPlotBuffer = {}

    for country in countries:

        figure, axes = plt.subplots(figsize = PLOT_SIZE_TINY)
        data = [
            (sum(1 for ln in successfulLaunchesByYear[y] if ln.Country == country),
             sum(1 for ln in failedLaunchesByYear[y] if ln.Country == country))
            for y in years
        ]

        maximumYearlyCount = max(s for s, _ in data)
        if maximumYearlyCount > 1:  # For maximum equal to one the line makes the actual launch marks unreadable.
            plt.axhline(y = maximumYearlyCount, **LINE_ARGUMENTS)

        plt.text(H_LINE_TEXT_POSITION, maximumYearlyCount + H_LINE_TEXT_OFFSET, maximumYearlyCount, **H_LINE_TEXT_ARGUMENTS)

        axes.bar(years, [s for s, _ in data], color = COLORS[country])
        axes.bar(years, [f for _, f in data], color = COLORS["Failure"], bottom = [s for s, _ in data])

        axes.set_title(Translated(country), fontsize = 14.0)
        axes.xaxis.set_major_locator(MultipleLocator(10))
        axes.set_ylabel(Translated("Launches"))

        axes.get_yaxis().set_visible(False)
        axes.spines["left"].set_visible(False)

        if launchCountUpperRange is None:
            launchCountUpperRange = axes.get_ylim()[1]
        else:
            axes.set_ylim([0, launchCountUpperRange])

        countryPlotBuffer[country] = BytesIO()
        plt.savefig(countryPlotBuffer[country], format = "png")
        plt.close()
        countryPlotBuffer[country].seek(0)

        console.print(f"Generated plot for: {country}.")

    console.print("All plots generated.")

    # Create the "Selected Rocket Families" plot.

    console.print()
    console.print(f'[bold]\[{CurrentLanguage}] Generating the "Selected Rocket Families" plot...[/bold]')

    data = {f: {y: sum(ln.Family == f for ln in successfulLaunchesByYear[y]) for y in years} for f in ROCKET_FAMILIES}
    totalSums = {f: sum(data[f].values()) for f in ROCKET_FAMILIES}  # Total number of successful launches for each family.

    figure, axes = plt.subplots(figsize = PLOT_SIZE_EXTRA_LONG)
    currentBottom = [0] * len(years)

    for family in ROCKET_FAMILIES:

        label = f"{Translated(family)} ({totalSums[family]})"
        axes.bar(years, data[family].values(), label = label, bottom = currentBottom, color = COLORS[family])

        currentBottom = [x + y for x, y in zip(currentBottom, data[family].values(), strict = True)]

    axes.set_title(Translated("Launches of Selected Rocket Families"))
    axes.xaxis.set_major_locator(MultipleLocator(10))
    axes.set_ylabel(Translated("Launches"))
    axes.legend(ncol = len(ROCKET_FAMILIES))

    rocketFamiliesPlotBuffer = BytesIO()
    plt.savefig(rocketFamiliesPlotBuffer, format = "png")
    plt.close()
    rocketFamiliesPlotBuffer.seek(0)

    console.print("Plot generated.")

    # Create the "Rocket Family" plots.

    console.print()
    console.print(f'[bold]\[{CurrentLanguage}] Generating the "Rocket Family" plots for individual rocket families...[/bold]')

    launchCountUpperRange = None

    familyPlotBuffer = {}

    for family in ROCKET_FAMILIES:

        figure, axes = plt.subplots(figsize = PLOT_SIZE_TINY)
        data = [
            (sum(1 for ln in successfulLaunchesByYear[y] if ln.Family == family),
             sum(1 for ln in failedLaunchesByYear[y] if ln.Family == family))
            for y in years
        ]

        maximumYearlyCount = max(s for s, _ in data)
        plt.axhline(y = maximumYearlyCount, **LINE_ARGUMENTS)
        plt.text(H_LINE_TEXT_POSITION, maximumYearlyCount + H_LINE_TEXT_OFFSET, maximumYearlyCount, **H_LINE_TEXT_ARGUMENTS)

        axes.bar(years, [s for s, _ in data], color = COLORS[family])
        axes.bar(years, [f for _, f in data], color = COLORS["Failure"], bottom = [s for s, _ in data])

        axes.set_title(Translated(family), fontsize = 14.0)
        axes.xaxis.set_major_locator(MultipleLocator(10))
        axes.set_ylabel(Translated("Launches"))

        axes.get_yaxis().set_visible(False)
        axes.spines["left"].set_visible(False)

        if launchCountUpperRange is None:
            launchCountUpperRange = axes.get_ylim()[1]
        else:
            axes.set_ylim([0, launchCountUpperRange])

        familyPlotBuffer[family] = BytesIO()
        plt.savefig(familyPlotBuffer[family], format = "png")
        plt.close()
        familyPlotBuffer[family].seek(0)

        console.print(f"Generated plot for: {family}.")

    console.print("All plots generated.")

    # Create the final image.

    console.print()
    console.print(f"[bold]\[{CurrentLanguage}] Creating the final image...[/bold]")

    image = Image.new("RGBA", (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX))
    image.paste(ImageColor.getcolor(COLORS["Background"], "RGBA"), (0, 0, *image.size))
    verticalPosition = 0

    image.paste(Image.open(allLaunchesPlotBuffer), (0, verticalPosition))
    image.paste(Image.open(successesFailuresPlotBuffer), (int(PLOT_SIZE_LONG[0] * DPI) + SPACING_PX, verticalPosition))
    verticalPosition += int(PLOT_SIZE_LONG[1] * DPI) + SPACING_PX

    for index, country in enumerate(countries):
        countryPlotImage = Image.open(countryPlotBuffer[country])
        image.paste(countryPlotImage, ((countryPlotImage.size[0] + SPACING_PX) * index, verticalPosition))

    verticalPosition += int(PLOT_SIZE_TINY[1] * DPI) + 2 * SPACING_PX

    image.paste(Image.open(rocketFamiliesPlotBuffer), (0, verticalPosition))
    verticalPosition += int((PLOT_SIZE_EXTRA_LONG[1] * DPI) + SPACING_PX)

    for index, family in enumerate(ROCKET_FAMILIES):
        familyPlotImage = Image.open(familyPlotBuffer[family])
        image.paste(familyPlotImage, ((familyPlotImage.size[0] + SPACING_PX) * index, verticalPosition))

    verticalPosition += int(PLOT_SIZE_TINY[1] * DPI) + SPACING_PX

    paddedImage = Image.new("RGBA", (IMAGE_WIDTH_PX + 2 * SPACING_PX, IMAGE_HEIGHT_PX + 2 * SPACING_PX))
    paddedImage.paste(ImageColor.getcolor(COLORS["Background"], "RGBA"), (0, 0, *paddedImage.size))
    paddedImage.paste(image, (SPACING_PX, SPACING_PX))
    paddedImage.save(f"Output Image ({CurrentLanguage}).png")

    console.print("The image has been saved.")
