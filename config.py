'''
  ******************************************************************************************
      Assembly:                iyr
      Filename:                config.py
      Author:                  Terry D. Eppler
      Created:                 05-31-2022

      Last Modified By:        Terry D. Eppler
      Last Modified On:        05-01-2025
  ******************************************************************************************
  <copyright file="config.py" company="Terry D. Eppler">

	     config.py
	     Copyright ©  2022  Terry Eppler

     Permission is hereby granted, free of charge, to any person obtaining a copy
     of this software and associated documentation files (the “Software”),
     to deal in the Software without restriction,
     including without limitation the rights to use,
     copy, modify, merge, publish, distribute, sublicense,
     and/or sell copies of the Software,
     and to permit persons to whom the Software is furnished to do so,
     subject to the following conditions:

     The above copyright notice and this permission notice shall be included in all
     copies or substantial portions of the Software.

     THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
     INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
     FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT.
     IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
     DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
     ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
     DEALINGS IN THE SOFTWARE.

     You can contact me at:  terryeppler@gmail.com or eppler.terry@epa.gov

  </copyright>
  <summary>
    config.py
  </summary>
  ******************************************************************************************
'''
import os
from typing import Optional, List, Dict
from pathlib import Path
import streamlit.components.v1 as components

# ------------ CONSTANT
BLUE_DIVIDER = "<div style='height:1.5px;align:left;background:#0078FC;margin:20px 0px 30px 0px;'></div>"
APP_TITLE = 'Iyrin'
APP_SUBTITLE = 'Geospatial Toolkit'
DB_PATH = 'stores/sqlite/data.db'
DEFAULT_DATA = r'UAP Sightings'
BASE_DIR = Path( __file__ ).resolve( ).parent
FAVICON = r'resources/images/favicon.ico'
LOGO = r'resources/images/iyrin-logo.png'
MAP_ID = r'16b56ad08af295ded24d8eb2'
MAP_NAME = r'uap-static'
DATASET_ID = r'5adda1cd-f412-4ed5-874d-e97664f229b4'
DATASET_NAME = r'data'
STYLE_ID = r'86d00019936c16f936cc936c'
STYLE_NAME = r'uap-dark'

# ----------- API KEYS

AIRNOW_API_KEY = os.getenv( 'AIRNOW_API_KEY' )
CLAUDE_API_KEY = os.getenv( 'CLAUDE_API_KEY' )
CONGRESS_API_KEY = os.getenv( 'CONGRESS_API_KEY' )
CHROMA_API_KEY = os.getenv( 'CHROMA_API_KEY' )
CHROMA_TENET_ID = os.getenv( 'CHROMA_TENET_ID' )
GEOAPIFY_API_KEY = os.getenv( 'GEOAPIFY_API_KEY' )
GEOCODING_API_KEY = os.getenv( 'GEOCODING_API_KEY' )
GEMINI_API_KEY = os.getenv( 'GEMINI_API_KEY' )
GOOGLE_API_KEY = os.getenv( 'GOOGLE_API_KEY' )
GOOGLEMAPS_API_KEY = os.getenv( 'GOOGLEMAPS_API_KEY' )
GOOGLE_CSE_ID = os.getenv( 'GOOGLE_CSE_ID' )
GOOGLE_CLOUD_PROJECT_ID = os.getenv( 'GOOGLE_CLOUD_PROJECT_ID' )
GOOGLE_CLOUD_LOCATION = os.getenv( 'GOOGLE_CLOUD_LOCATION' )
GOVINFO_API_KEY = os.getenv( 'GOVINFO_API_KEY' )
GOOGLE_GENAI_USE_VERTEXAI = os.getenv( 'GOOGLE_GENAI_USE_VERTEXAI' )
GOOGLE_WEATHER_API_KEY = os.getenv( 'GOOGLE_WEATHER_API_KEY' )
GOOGLE_ACCOUNT_FILE = os.getenv( 'GOOGLE_ACCOUNT_CREDENTIALS' )
GOOGLE_DRIVE_TOKEN_PATH = os.getenv( 'GOOGLE_DRIVE_TOKEN_PATH' )
GOOGLE_DRIVE_FOLDER_ID = os.getenv( 'GOOGLE_DRIVE_FOLDER_ID' )
HUGGINGFACE_API_KEY = os.getenv( 'HUGGINGFACE_API_KEY' )
IPINFO_API_KEY = os.getenv( 'IPINFO_API_KEY' )
OPENAI_API_KEY = os.getenv( 'OPENAI_API_KEY' )
PINECONE_API_KEY = os.getenv( 'PINECONE_API_KEY' )
LANGSMITH_API_KEY = os.getenv( 'LANGSMITH_API_KEY' )
LLAMAINDEX_API_KEY = os.getenv( 'LLAMAINDEX_API_KEY' )
LLAMACLOUD_API_KEY = os.getenv( 'LLAMACLOUD_API_KEY' )
MISTRAL_API_KEY = os.getenv( 'MISTRAL_API_KEY' )
NASA_API_KEY = os.getenv( 'NASA_API_KEY' )
NASA_EARTHDATA_TOKEN = os.getenv( 'NASA_EARTHDATA_TOKEN' )
NEWS_API_KEY = os.getenv( 'NEWSAPI_API_KEY' )
THENEWS_API_KEY = os.getenv( 'THENEWSAPI_API_KEY' )
WEATHERAPI_API_KEY = os.getenv( 'WEATHERAPI_API_KEY' )
XAI_API_KEY = os.getenv( 'XAI_API_KEY' )
O365_CLIENT_ID = os.getenv( 'O365_CLIENT_ID' )
O365_CLIENT_SECRET = os.getenv( 'O365_CLIENT_SECRET' )
OPENAQ_API_KEY = os.getenv( 'OPENAQ_API_KEY' )
OPENSKY_CLIENT_ID = os.getenv( 'OPENSKY_CLIENT_ID' ) or os.getenv( 'OPENSKY_API_CLIENT_ID' )
OPENSKY_API_CLIENT_SECRET = os.getenv( 'OPENSKY_API_CLIENT_SECRET' ) or os.getenv( 'OPENSKY_API_CREDENTIALS' )
OPENSKY_API_CREDENTIALS = OPENSKY_API_CLIENT_SECRET
CENSUS_API_KEY = os.getenv( 'CENSUS_API_KEY' )
SOCRATA_API_KEY = os.getenv( 'SOCRATA_API_KEY' )
HEALTHDATA_API_KEY = os.getenv( 'HEALTHDATA_API_KEY' )
USGS_WATERDATA_API_KEY = os.getenv( 'USGS_WATERDATA_API_KEY' ) or os.getenv( 'USGS_API_KEY' )
DATA_GOV_API_KEY = os.getenv( 'DATAGOV_API_KEY' )
GOVINFO_API_KEY = os.getenv( 'GOVINFO_API_KEY' )
FIRMS_MAP_KEY = os.getenv( 'FIRMS_MAP_KEY' ) or os.getenv( 'NASA_FIRMS_MAP_KEY' )
PURPLEAIR_API_KEY = os.getenv( 'PURPLEAIR_API_KEY' )
SKYMAP_TOKEN = os.getenv( 'SKY_MAP_TOKEN' )


# -------------- SETTINGS

MODES = [ 'Mapping Tools', 'Interactive Map', 'Local Data', 'Geoscience Data',
          'Astronomical Data', 'Celestial Map', 'Public Health', 'Artificial Intelligence',
          'File Upload', 'Data Management' ]


AGENTS = ( 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
		'AppleWebKit/537.36 (KHTML, like Gecko) '
		'Chrome/147.0.0.0 Safari/537.36' )

# ----------------- Models

GPT_MODELS = [ 'gpt-5.4', 'gpt-5', 'gpt-5-mini', 'gpt-5-nano',
               'gpt-5.1', 'gpt-5.2', 'gpt-4.1' ]

GEMINI_MODELS = [ 'gemini-2.5-flash', 'gemini-2.5-flash-lite',
                  'gemini-2.5-flash-lite' ]

GROK_MODELS = [ 'grok-4-1-fast-reasoning', 'grok-4-fast-reasoning', 'grok-4',
                'grok-code-fast-1', 'grok-3-mini', 'grok-2-image-1212' ]

CLAUDE_MODELS = [ 'claude-opus-4-6', 'claude-sonnet-4-6',
                  'claude-haiku-4-5' ]

MISTRAL_MODELS = [ 'mistral-large-latest', 'mistral-medium-latest',
                   'mistral-small-latest', 'mistral-ocr-latest'  ]

# -------- LOADER DEFINITIONS -------------------

TEXT_LOADER = r'''Provides LangChain's TextLoader functionality to parse plain-text files
into Document objects.

https://reference.langchain.com/python/langchain-community/document_loaders/text/TextLoader
'''

NLTK_LOADER = r'''The Natural Language Toolkit (NLTK) is a comprehensive, open-source Python library
used for symbolic and statistical Natural Language Processing (NLP). Developed originally at
the University of Pennsylvania by Steven Bird and Edward Loper, it has become a standard tool
in academia for teaching and research in computational linguistics.

https://www.nltk.org/
'''

HTML_LOADER = r'''Provides Langchain's UnstructuredHTMLLoader's functionality to parse HTML files
into Document objects. You can run the loader in one of two modes: "single" and "elements".
If you use "single" mode, the document will be returned as a single langchain Document object.
If you use "elements" mode, the unstructured library will split the document into elements
such as Title and NarrativeText. You can pass in additional unstructured kwargs after mode
to apply different unstructured settings.

https://reference.langchain.com/python/langchain-community/document_loaders/html/UnstructuredHTMLLoader
'''

EMAIL_LOADER = r'''Uses Langchain's UnstructuredEmail Loader to parse Email files into document
objects. You can run the loader in one of two modes: "single" and "elements".
If you use "single" mode, the document will be returned as a single langchain Document object.
If you use "elements" mode, the unstructured library will split the document into elements
such as Title and NarrativeText. You can pass in additional unstructured kwargs after mode
to apply different unstructured settings.

https://reference.langchain.com/python/langchain-community/document_loaders/email/UnstructuredEmailLoader
'''

WEB_CRAWLER = r'''Web fetching with optional Playwright-backed page rendering.
'''

WEB_LOADER = r'''Functionality to load all text from HTML webpages into
a document format that can be used downstream.

https://reference.langchain.com/python/langchain-community/document_loaders/web_base/WebBaseLoader
'''

GITHUB_LOADER = r'''The LangChain GitHub Loader is a suite of integrations designed to ingest data
from GitHub repositories into a format compatible with Large Language Models (LLMs).
These loaders are primarily used in Retrieval-Augmented Generation (RAG) pipelines to
allow AI agents to "chat" with codebases, analyze issues, or summarize pull requests.

https://reference.langchain.com/python/langchain-community/document_loaders/github/GithubFileLoader
'''

WIKIPEDIA_LOADER = r'''The LangChain Wikipedia Loader (WikipediaLoader) is a component designed to
fetch and convert Wikipedia pages into a standardized Document format for use in LLM applications.

https://reference.langchain.com/python/langchain-community/document_loaders/wikipedia/WikipediaLoader
'''

ARXIV_LOADER = r'''arXiv is a free distribution service and an open-access archive for nearly 2.4 million
scholarly articles in the fields of physics, mathematics, computer science, quantitative
biology, quantitative finance, statistics, electrical engineering and systems science, and
economics. Materials on this site are not peer-reviewed by arXiv.

https://reference.langchain.com/python/langchain-community/document_loaders/arxiv/ArxivLoader
'''

PDF_LOADER = r'''Public, SDK-oriented PDF loader with: Page-aware metadata, Two-stage chunking,
Configurable chunk profiles, Table isolation, Optional OCR fallback.

https://reference.langchain.com/python/langchain-community/document_loaders/pdf/PyPDFLoader
'''

PUBMED_LOADER = r'''A document loader class designed to fetch up to a specified number of documents
directly from the PubMed biomedical library into LangChain Document objects.

https://reference.langchain.com/python/langchain-community/document_loaders/pubmed/PubMedLoader
'''

EXCEL_LOADER = r'''Provides LangChain's UnstructuredExcelLoader functionality
to parse Excel spreadsheets into documents.

https://reference.langchain.com/python/langchain-community/document_loaders/excel/UnstructuredExcelLoader
'''

POWERPOINT_LOADER = r'''The UnstructuredPowerPointLoader (within LangChain) is a tool for parsing
Microsoft PowerPoint (.ppt/.pptx) files to extract text and metadata, enabling AI applications
to read and process presentations. It supports loading documents in "single" (full text) or
"elements" (chunked by title/narrative) modes, ideal for Retrieval Augmented Generation (RAG) tasks

https://reference.langchain.com/python/langchain-community/document_loaders/powerpoint/UnstructuredPowerPointLoader
'''

JSON_LOADER = r'''The LangChain JSONLoader is a specialized document loader used to transform JSON
and JSON Lines data into standardized LangChain Document objects. It is a critical component
for building applications like Retrieval-Augmented Generation (RAG) that need to process structured data.

https://reference.langchain.com/python/langchain-community/document_loaders/json_loader/JSONLoader
'''

MARKDOWN_LOADER = r'''LangChain's Markdown document loaders are specialized tools used to convert
Markdown files into standardized LangChain Document objects. These objects are then used
for downstream tasks like Retrieval Augmented Generation (RAG), embedding generation,
or semantic chunking.

https://reference.langchain.com/python/langchain-community/document_loaders/markdown/UnstructuredMarkdownLoader
'''

XML_LOADER = r'''The UnstructuredXMLLoader in LangChain is a specialized tool designed to load and
parse XML files into standardized LangChain Document objects. It leverages the Unstructured.io
library to extract text content and preserve document structure for use in downstream LLM
applications like RAG.

https://reference.langchain.com/python/langchain-community/document_loaders/xml/UnstructuredXMLLoader
'''

CSV_LOADER = r'''The LangChain CSVLoader is a standard utility within the langchain-community package
designed to transform structured CSV data into a list of standardized Document objects.
This process is the foundational step for integrating tabular data into LLM-powered workflows,
such as Retrieval Augmented Generation (RAG).

https://reference.langchain.com/python/langchain-community/document_loaders/csv_loader/CSVLoader
'''

WORD_LOADER = '''Works with both .docx and .doc files. You can run the loader in one of two modes:
"single" and "elements". If you use "single" mode, the document will be returned as a
single langchain Document object. If you use "elements" mode, the unstructured library will
split the document into elements such as Title and NarrativeText.

https://reference.langchain.com/python/langchain-community/document_loaders/word_document/UnstructuredWordDocumentLoader
'''

NOTEBOOK_LOADER = '''Loads .ipynb notebook files.

https://reference.langchain.com/python/langchain-community/document_loaders/notebook/NotebookLoader
'''

GOOGLE_CLOUD_FILE_LOADER = r'''
'''

GOOGLE_CLOUD_BUCKET_LOADER = r'''Google Cloud Storage (GCS) Bucket Loader is a tool that lets you
pull text and files out of a Google Cloud bucket so your AI application can read them. This is super
helpful when you want to build a Retrieval-Augmented Generation (RAG) system, which lets an AI
answer questions using your own private files.

https://docs.langchain.com/oss/python/integrations/document_loaders/google_cloud_storage_file
'''

GOOGLE_CLOUD_FILE_LOADER = r'''The Google Cloud file loaders in LangChain are tools used to pull
files and data out of Google Cloud Storage (GCS) and turn them into text format that an
Artificial Intelligence (AI) can read.

https://docs.langchain.com/oss/python/integrations/document_loaders/google_cloud_storage_file
'''

AWS_FILE_LOADER = r'''A tool that pulls documents and data from an Amazon Web Services (AWS) S3
bucket so an AI can read them. It acts like a bridge between your cloud storage and your large
language model (LLM), which is very helpful for building Retrieval-Augmented Generation (RAG) applications

https://reference.langchain.com/python/langchain-community/document_loaders/s3_file/S3FileLoader
'''

AWS_S3FILE_LOADER = r'''An S3FileLoader is a software component used in data frameworks and AI libraries
to read files directly from an Amazon AWS S3 bucket. It is commonly used in tools like LangChain
Community S3FileLoader and PyTorch DataPipe S3FileLoader to parse text, PDFs, or binary data for applications

https://reference.langchain.com/python/langchain-community/document_loaders/s3_file/S3FileLoader
'''

ONEDRIVE_LOADER = r'''A document laoder in LangChain is a specialized tool designed to load and
parse One Drive files into standardized LangChain Document objects to extract text content and
preserve document structure for use in downstream LLM
applications like RAG.

https://reference.langchain.com/python/langchain-community/document_loaders/onedrive/OneDriveLoader
'''

# --------------- API

AIR_NOW = r'''AirNow is the official U.S. government website and app providing real-time,
local air quality data and forecasts using the color-coded Air Quality Index (AQI).
It covers ozone and particle pollution ( and  ) via a partnership of the EPA, NOAA, and
local agencies, offering a "Fire and Smoke Map" to monitor smoke impacts.

https://docs.airnowapi.org/
'''

PURPLE_AIR = r'''PurpleAir provides low-cost, real-time air quality monitors and a public,
crowdsourced map to measure, visualize, and share hyper-local,, particulate matter data.
Using laser counters, these sensors empower communities to track pollution, particularly
during wildfire events. Data is accessible via the PurpleAir Map and is used by researchers,
public agencies, and individuals worldwide.

https://api.purpleair.com/
'''

OPEN_AQ = r'''OpenAQ is a non-profit organization that aggregates, harmonizes, and shares open-source,
global air quality data to fight "air inequality". It provides real-time and historical
data—primarily on PM2.5, PM10, and other pollutants—from over 48,000 locations across 150 c
ountries. The platform empowers researchers, journalists, and communities to access, analyze,
and use air quality data through an open API, fostering collaboration to improve public
health and policy.

https://docs.openaq.org/
'''

NOAA_CLIMATE_DATA = r'''NOAA climate data is provided primarily through the National Centers for
Environmental Information (NCEI), serving as the world's largest archive of atmospheric,
coastal, and geophysical data. It offers free access to historical weather records, 30-year
Climate Normals, and datasets on temperature, precipitation, and storms. Data is accessible
via the NCEI Climate Data Online (CDO) portal.

https://www.ncdc.noaa.gov/cdo-web/
'''

USGS_NATIONAL_MAP = r'''The USGS National Map is a premier collaborative program providing free,
accurate, and public domain geospatial data for the United States and its territories.
It offers topographic maps, 3D elevation data, and 8+ data layers (transportation,
hydrography, structures) via an online viewer, data downloads, and web services for public,
academic, and government use.

https://tnmaccess.nationalmap.gov/api/v1/docs
'''

USGS_EARTHQUAKES = r'''The USGS Earthquake Hazards Program monitors, reports, and researches global
seismic activity to reduce losses and save lives. It operates the National Earthquake
Information Center (NEIC) and Advanced National Seismic System (ANSS) to detect magnitude,
location, and impacts, providing data for public safety, engineering, and hazard assessments

https://earthquake.usgs.gov/fdsnws/event/1/
'''

USGS_WATER = r'''The USGS Water Resources Mission Area monitors, assesses, and conducts research on
the nation's water, providing data on streamflow, groundwater, water quality, and water use.

https://api.waterdata.usgs.gov/
'''

NOAA_TIDES_CURRENTS = r'''NOAA Tides & Currents, managed by the Center for Operational Oceanographic
Products and Services (CO-OPS), is the authoritative U.S. source for water level, tidal, and
oceanographic data. It offers real-time monitoring and predictions for over 3,000 stations,
crucial for navigation, safety, and coastal resilience.

https://tidesandcurrents.noaa.gov/web_services_info.html
'''

STAR_MAP = r'''Provides static and link-based star chart generation using the SKY-MAP.ORG
XML API, Site Linker, and Image Generator interfaces.

https://starmap360.com/blog/starmap-api-for-developers-and-sellers/
'''

NASA_OPEN_SCIENCE = r'''NASA’s Open Science Data Repository (OSDR) enables the reuse of comprehensive,
multi-modal space life science data—including omics, physiological, phenotypic, behavioral,
and environmental telemetry—to advance basic and applied research as well as operational
outcomes for human space exploration.

https://api.nasa.gov/#open-science-data-repository
'''

OPEN_SKY = r'''The OpenSky Network consists of a multitude of sensors connected to the Internet by
volunteers, industrial supporters, and academic/governmental organizations. All collected
raw data is archived in a large historical database. The database is primarily used by
researchers from different areas to analyze and improve air traffic control technologies
and processes. The main technologies behind the OpenSky Network are the Automatic Dependent
Surveillance-Broadcast (ADS-B) and Mode S. These technologies provide detailed (live) aircraft
information over the publicly accessible 1090 MHz radio frequency channel.

https://opensky-network.org/data/api
'''

EPA_ENVIROFACTS = r'''The Envirofacts Data Warehouse contains information from select EPA Environmental
program office databases and provides access about environmental activities that may affect air,
water, and land anywhere in the United States.

https://www.epa.gov/enviro/envirofacts-data-service-api
'''

EPA_UV_INDEX = r'''The EPA UV Index predicts daily solar UV radiation intensity on a 1–11+ scale,
helping to gauge sun-safe precautions. Developed with the National Weather Service, it factors
in ozone, clouds, and elevation to forecast noon intensity. A UV Alert is issued if the
index is 6+ and unusually high.

https://www.epa.gov/enviro/web-services#uvindex
'''

NASA_EONET = r'''NASA Earth Observatory's Natural Event Tracker (EONET) allows users to access imagery,
often in near real-time (NRT), of natural events such as dust storms, forest fires, and tropical
cyclones—empowering people all across the planet to locate, track, and potentially prepare for
and manage events that affect communities in their paths. The EONET application programming
interface (API) provides customization of features including curation and direct links to
image sources.

https://eonet.gsfc.nasa.gov/docs/v2.1
'''

NASA_FIRMS = r'''NASA’s Fire Information for Resource Management System (FIRMS) provides near
real-time, satellite-derived active fire and hotspot data (within 3 hours of observation)
to monitor wildfires. Using sensors from MODIS and VIIRS, it offers global coverage through
an interactive map, email alerts, and GIS data. It is designed for firefighters, scientists,
and natural resource managers.

https://firms.modaps.eosdis.nasa.gov/api/
'''

OPEN_WEATHER = r''' Open-Meteo leverages a powerful combination of global (11 km) and mesoscale (1 km) weather
models from esteemed national weather services, providing comprehensive forecasts with
remarkable precision.

https://open-meteo.com/en/docs
'''

HISTORICAL_WEATHER = r'''Provides historical weather retrieval by location name and date using the
Open-Meteo Geocoding API and Open-Meteo Historical Weather API. This class is intentionally
designed around the actual user-facing need in the Foo fetcher expander: enter a location
and a date, resolve that location to coordinates, then retrieve historical weather for that date.

https://open-meteo.com/en/docs/historical-weather-api
'''

ASTRONOMY_CATALOG = r'''The Open Astronomy Catalog (OAC) API is a RESTful interface designed for
programmatic access to open-access astronomical data, specifically focusing on transient events.

https://astrocats.space/
'''

ASTRO_QUERY = r'''Access to the astropy package that contains key functionality and common tools needed for
performing astronomy and astrophysics with Python. It is at the core of the Astropy Project,
which aims to enable the community to develop a robust ecosystem of affiliated packages
covering a broad range of needs for astronomical research, data processing, and data analysis.

https://docs.astropy.org/en/stable/
'''

US_NAVAL_OBSERVATORY = r'''Provides access to APIs from the US Naval Observatory's Celestial Navigation Data for
Assumed Position and Time:  this data service provides all the astronomical information
necessary to plot navigational lines of position from observations of the altitudes of
celestial bodies.

https://aa.usno.navy.mil/data/api
'''

GOOGLE_CSE = r'''The Cse Service is the endpoint that returns the requested searches.
You must identify a particular search engine to use in your request
(using the cx query parameter) as well as the search query (using the q query parameter).
In addition, you should provide a developer key (using the key query parameter).
'''

GOOGLE_WEATHER = r'''The Google Weather API lets you request real-time, hyperlocal weather data for
locations around the world. Weather information includes temperature, precipitation,
humidity, and more. Include the latitude and longitude coordinates of the location in your
request URL parameters.

https://developers.google.com/maps/documentation/weather/overview
'''

NASA_GLOBAL_IMAGERY = r'''NASA's Global Imagery Browse Services (GIBS) system provides visualizations
of NASA Earth Science observations through standardized web services. These services deliver
global, full-resolution visualizations of satellite data to users in a highly responsive manner,
enabling visual discovery of scientific phenomena, supporting timely decision-making for
natural hazards, educating the next generation of scientists, and making imagery of the planet
more accessible to the media and public. Browse all of these visualizations through our
Worldview application.

https://nasa-gibs.github.io/gibs-api-docs/
'''

CDC_WONDER = r'''Wide-ranging ONline Data for Epidemiologic Research -- an easy-to-use, menu-driven
system that makes the information resources of the Centers for Disease Control and
Prevention (CDC) available to public health professionals and the public at large. It provides
access to a wide array of public health information.

https://wonder.cdc.gov/wonder/help/wonder-api.html
'''

SPACE_WEATHER = r'''The Space Weather Database Of Notifications, Knowledge, Information (DONKI) is
a comprehensive on-line tool for space weather forecasters, scientists, and the general
space science community. DONKI chronicles the daily interpretations of space weather
observations, analysis, models, forecasts, and notifications provided by the Space Weather
Research Center (SWRC), comprehensive knowledge-base search functionality to support anomaly
resolution and space science research, intelligent linkages, relationships, cause-and-effects
between space weather activities and comprehensive webservice API access to information
stored in DONKI.

https://ccmc.gsfc.nasa.gov/tools/DONKI/
'''

STAR_CHART = r'''Provides static and link-based star chart generation using the SKY-MAP.ORG
XML API, Site Linker, and Image Generator interfaces.

https://sky-map.org/?locale=EN
'''

SATELLITE_CENTER = r'''The Satellite Situation Center Web (SSCWeb) Service is operated by NASA's
Space Physics Data Facility (SPDF). It was developed jointly by SPDF and the National Space
Science Data Center (NSSDC) to support a range of NASA science programs and to fulfill key
international NASA responsibilities including those of NSSDC and the World Data Center-A
for Rockets and Satellites.

https://sscweb.gsfc.nasa.gov/
'''

PUB_MED_SEARCH_LOADER = r''' Queries the PubMed biomedical library to fetch publication summaries and
abstracts as LangChain Document objects.

https://reference.langchain.com/python/langchain-community/document_loaders/pubmed/PubMedLoader
'''

OPEN_CITY_DATA_LOADER = r'''Designed to load open data records directly from Open City datasets
into LangChain Document objects.

https://reference.langchain.com/python/langchain-community/document_loaders/open_city_data/OpenCityDataLoader
'''

UN_DATA = r'''Provides dynamic, programmatic access to data within the UNdata platform. Developers
can use the API to dynamically query UNdata to obtain the latest data and display the result on a
Web page, download to local storage for further processing, etc. UNdata API is powered by Eurostat’s
SDMX Reference Infrastructure (SDMX-RI). The API is implemented as a SOAP Web Service that can be
used to query the datamarts using the SDMX standard. The API is governed by UNdata Terms of Use.

http://data.un.org/Host.aspx?Content=API
'''

CENSUS_DATA = r'''The American Community Survey (ACS) is the premier source of detailed information
about the nation's people and housing. As an ongoing survey conducted by the U.S. Census Bureau since
2005, the ACS collects detailed social, economic, housing, and demographic information from a sample
of households across the 50 states, the District of Columbia, and Puerto Rico

https://data.census.gov/
'''

CDC_SOCRATA = r'''It provides information uniformly on this large scale for local areas at four
geographic levels. Estimates were provided by the Centers for Disease Control and Prevention (CDC),
Division of Population Health, Epidemiology and Surveillance Branch. PLACES was funded by the
Robert Wood Johnson Foundation in conjunction with the CDC Foundation. This dataset includes
estimates for 40 measures: 12 for health outcomes, 7 for preventive services use, 4 for chronic
disease-related health risk behaviors, 7 for disabilities, 3 for health status, and 7 for
health-related social needs. These estimates can be used to identify emerging health problems and
to help develop and carry out effective, targeted public health prevention activities
(ex https://cdc.gov{resource-id}.json)

https://dev.socrata.com/foundry/data.cdc.gov/swc5-untb
'''

US_HEALTH_DATA = r'''Health & Human Services Open Data to inform decisions by the public and
policymakers, drive innovation and economic activity, accelerate scientific research, and
strengthen the foundation of an open and transparent government.

https://healthdata.gov/login
'''

WHO_DATA = r'''The GHO portal provides a simple query interface to the World Health Organization's
data and statistics content, using OData (Open Data Protocol)

https://www.who.int/data/gho/info/gho-odata-api
'''

WORLD_POP_DATA = r'''WorldPop is an interdisciplinary research group based at the University of
Southampton, bringing together around 40 researchers, data scientists, and specialists. Their work
focuses on improving population data at local levels and helping ensure it is used effectively for
health, development, and humanitarian action, including tracking progress towards the
Sustainable Development Goals (SDGs).

https://www.worldpop.org/sdi/introapi/
'''

OPENSKY_NETWORK = r'''Live air traffic surveillance data. Operating via thousands of volunteer-run
sensors worldwide, it captures raw ADS-B, Mode S, and FLARM signals. It stores complete, unfiltered
historical data to support academic, scientific, and institutional research on airspace
safety and efficiency.

https://openskynetwork.github.io/opensky-api/rest.html
'''