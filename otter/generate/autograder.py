"""
Gradescope autograder configuration generator for Otter Generate
"""

import os
import shutil
import subprocess
import pathlib
import pkg_resources

from glob import glob
from subprocess import PIPE
from jinja2 import Template

from .token import APIClient

TEMPLATES_DIR = pkg_resources.resource_filename(__name__, "templates")
SETUP_SH_PATH = os.path.join(TEMPLATES_DIR, "setup.sh")
PYTHON_REQUIREMENTS_PATH = os.path.join(TEMPLATES_DIR, "requirements.txt")
R_REQUIREMENTS_PATH = os.path.join(TEMPLATES_DIR, "requirements.r")
RUN_AUTOGRADER_PATH = os.path.join(TEMPLATES_DIR, "run_autograder")
MINICONDA_INSTALL_URL = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"

with open(SETUP_SH_PATH) as f:
    SETUP_SH = Template(f.read())

with open(PYTHON_REQUIREMENTS_PATH) as f:
    PYTHON_REQUIREMENTS = Template(f.read())

with open(R_REQUIREMENTS_PATH) as f:
    R_REQUIREMENTS = Template(f.read())

with open(RUN_AUTOGRADER_PATH) as f:
    RUN_AUTOGRADER = Template(f.read())

def main(args):
    """
    Runs ``otter generate autograder``
    """
    assert args.threshold is None or 0 <= args.threshold <= 1, "{} is not a valid threshold".format(
        args.threshold
    )

    if args.course_id or args.assignment_id:
        assert args.course_id and args.assignment_id, "Either course ID or assignment ID unspecified for PDF submissions"
        if not args.token:
            args.token = APIClient.get_token()

    # check that args.public_multiplier is valid
    assert 0 <= args.public_multiplier <= 1, f"Public test multiplier {args.public_multiplier} is not between 0 and 1"

    # check for valid language
    args.lang = args.lang.lower()
    assert args.lang.lower() in ["python", "r"], f"{args.lang} is not a supported language"

    # format run_autograder
    run_autograder = RUN_AUTOGRADER.render(
        threshold = str(args.threshold),
        points = str(args.points),
        show_stdout = str(args.show_stdout),
        show_hidden = str(args.show_hidden),
        seed = str(args.seed),
        token = str(args.token),
        course_id = str(args.course_id),
        assignment_id = str(args.assignment_id),
        filtering = str(not args.unfiltered_pdfs),
        pagebreaks = str(not args.no_pagebreaks),
        grade_from_log = str(args.grade_from_log),
        serialized_variables = str(args.serialized_variables),
        public_multiplier = str(args.public_multiplier),
        lang = str(args.lang.lower())
    )

    # format setup.sh
    setup_sh = SETUP_SH.render(
        autograder_dir = str(args.autograder_dir),
        miniconda_install_url = MINICONDA_INSTALL_URL,
        ottr_branch = "master",
    )

    # create tmp directory to zip inside
    os.mkdir("./tmp")

    try:
        # copy tests into tmp
        os.mkdir(os.path.join("tmp", "tests"))
        pattern = ("*.py", "*.[Rr]")[args.lang.lower() == "r"]
        for file in glob(os.path.join(args.tests_path, pattern)):
            shutil.copy(file, os.path.join("tmp", "tests"))

        # open requirements if it exists
        if os.path.isfile(args.requirements):
            f = open(args.requirements)
        else:
            assert args.requirements == "requirements.txt", f"requirements file {args.requirements} not found"
            f = open(os.devnull)

        # render the templates
        python_requirements = PYTHON_REQUIREMENTS.render(
            other_requirements = f.read() if args.lang.lower() == "python" else "",
            overwrite_requirements = False
        )

        # reset the stream
        f.seek(0)

        r_requirements = R_REQUIREMENTS.render(
            other_requirements = f.read() if args.lang.lower() == "r" else "",
            overwrite = args.overwrite_requirements
        )

        # close the stream
        f.close()
        
        # copy requirements into tmp
        with open(os.path.join(os.getcwd(), "tmp", "requirements.txt"), "w+") as f:
            f.write(python_requirements)

        with open(os.path.join(os.getcwd(), "tmp", "requirements.r"), "w+") as f:
            f.write(r_requirements)

        if r_requirements:
            with open(os.path.join(os.getcwd(), "tmp", "requirements.r"), "w+") as f:
                f.write(r_requirements)

        # write setup.sh and run_autograder to tmp
        with open(os.path.join(os.getcwd(), "tmp", "setup.sh"), "w+") as f:
            f.write(setup_sh)

        with open(os.path.join(os.getcwd(), "tmp", "run_autograder"), "w+") as f:
            f.write(run_autograder)

        # copy files into tmp
        if len(args.files) > 0:
            os.mkdir(os.path.join("tmp", "files"))

            for file in args.files:
                # if a directory, copy the entire dir
                if os.path.isdir(file):
                    shutil.copytree(file, str(os.path.join("tmp", "files", os.path.basename(file))))
                else:
                    # check that file is in subdir
                    file = os.path.abspath(file)
                    assert os.getcwd() in file, \
                        f"{file} is not in a subdirectory of the working directory"
                    wd_path = pathlib.Path(os.getcwd())
                    file_path = pathlib.Path(file)
                    rel_path = file_path.parent.relative_to(wd_path)
                    output_path = os.path.join("tmp", "files", rel_path)
                    os.makedirs(output_path, exist_ok=True)
                    shutil.copy(file, output_path)

        os.chdir("./tmp")

        zip_path = os.path.join("..", args.output_path, "autograder.zip")
        if os.path.exists(zip_path):
            os.remove(zip_path)

        zip_cmd = ["zip", "-r", zip_path, "run_autograder", "requirements.r",
                "setup.sh", "requirements.txt", "tests"]
        
        if r_requirements:
            zip_cmd += ["requirements.r"]

        if args.files:
            zip_cmd += ["files"]

        zipped = subprocess.run(zip_cmd, stdout=PIPE, stderr=PIPE)

        if zipped.stderr.decode("utf-8"):
            raise Exception(zipped.stderr.decode("utf-8"))

        # move back to tmp parent directory
        os.chdir("..")
    
    except:
        # delete tmp directory
        shutil.rmtree("tmp")

        # raise the exception
        raise
    
    else:
        # delete tmp directory
        shutil.rmtree("tmp")
