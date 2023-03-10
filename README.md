# Anatomical Region Labeling (ARL)
A deep-learning based anatomy region labeling for Cone-Beam Computed Tomography (CBCT) scans

This tool queries CBCT scans from an ARIA database (Varian Medical Systems, Palo Alto, CA) using a DICOM Query & Retrieval Tool (DQR) and classifies the scans into four distinct regions: head & neck, thoracic-abdominal, pelvis, and extremity. The ARL tool was implemented on Python 3.7/3.9 using Tensorflow 2.2. Algorithm training and testing was performed on an Nvidia Quadro P1000 4GB GPU system with 16 GB RAM.

## Requirements for the DQR:
1.	Trusted connection with Aria database:

    - To setup a Varian Daemon, please follow the instructions on the Varian API Book (https://varianapis.github.io/VarianApiBook.pdf), specifically in Chapter 4      (Daemons: a tour through Varian’s DICOM API).

    - The user will need two trusted entities (one for the Service Class Provider (SCP), and one for the Service Class User (SCU)). Once set up, please note the AE Title and Port Number of both trusted entities. Also note the AE Title, IP, and Port Number of the Aria server.

2.	Python Environment (Python 3.9)

    - The conda environment required for the DQR can be installed using the **dicom.yml** file present in the conda_envs folder

## Requirements for the CBCT image pre-processing and ARL model prediction:
1.	Python Environment (Python 3.7)

    - The conda environment required for the ARL can be installed using the **tensor6.yml** file present in the conda_envs folder

## Setting up the connection and output directories:
1.	Open the setup_information.json file using a text editor and adjust the following:

    - Input the connection settings (AE Title, Host IP, and Port Number) for the Aria server, and the two trusted entities.
  
    - staging_path: staging directory (“outputs” folder dir found in ARL_repo).
  
    - dicom_path: folder location where the dicom files will be saved.
  
    - archive_path: folder location where the dicom file information and model prediction will be archived.
  
    - report_path: folder location where the final report file (prediction) will be outputted.
  
    - log_path: folder location where the log file will be saved.
  
    - asset_path: folder path to the assets required to build the report (none currently).

**Pipeline_python.bat**: Queries pre-treatment CBCTs from the previous day for classification. *On first use: please open file with a text editor and adjust APPDIR to the current file directory and LOGFILE to the log_path directory.*

**Pipeline_python_by_date**: Queries CBCT data from the date inputted by user. Please use YYYY-MM-DD as the date format. *On first use: please open file with a text editor and adjust APPDIR to the current file directory and LOGFILE to the log_path directory.*

Example launch on cmd:
> */ARL_repo_dir/*> Pipeline_python_by_date 2022-12-06


## If you use part or all of this repository, please cite:
> **Luximon, D. C., Neylon, J., & Lamb, J. M. (2023). Feasibility of a deep-learning based anatomical region labeling tool for Cone-Beam Computed Tomography scans in Radiotherapy. Physics and Imaging in Radiation Oncology, 100427. https://doi.org/10.1016/j.phro.2023.100427**

## Support and Contact
If you have questions and/or suggestions - please contact me at dcluximon@gmail.com
