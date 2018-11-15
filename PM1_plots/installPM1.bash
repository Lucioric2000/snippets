#!/bin/bash
#You may install this software by downloading the compressed file via Github webpage or by its URL via wget <URL>, or using git with the command
sudo yum -y install sudo git
if [[ `expr match "$(pwd)" '.*\(PM1_plots\)'` = "PM1_plots" ]]
then
    echo "Already in PM1_plots folder."
    git pull origin master
elif [[ `expr match "$(pwd)" '.*\(snippets\)'` = "snippets" ]]
then
	echo "Already in snippets folder."
	cd PM1_plots
	git pull origin master
else
	echo "Not in snippets nor PM1_plots folder."
	repository_dir=/srv/qgen/snippets
    if [[ -d "${repository_dir}" ]]
    then
        cd "${repository_dir}/PM1_plots" && ./installPM1.bash $@
        exit
    elif [[ -e "${repository_dir}" ]]
    then
        echo "File ${repository_dir} exists but it is not a directory, thus we can not create a directory with that path tho hold the software reposotory. \
        See if it is safe to delete or move it, and then execute again this script."
    else
        sudo mkdir -p /srv/qgen
        sudo chmod -R 777 /srv/qgen
        cd /srv/qgen && git clone --recursive https://github.com/Lucioric2000/snippets
        cd "${repository_dir}/PM1_plots" && ./installPM1.bash $@
        exit
    fi

	git clone https://github.com/Lucioric2000/snippets /srv/qgen/snippets
	cd snippets/PM1_plots
fi

#git clone https://github.com/Lucioric2000/snippets
#cd snippets/PM1_plots

#For the first installs in the Centos server you should execute:
echo -e "[google-chrome]\\nname=google-chrome\\nbaseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64\\nenabled=1\\ngpgcheck=1\\ngpgkey=https://dl-ssl.google.com/linux/linux_signing_key.pub"|sudo tee /etc/yum.repos.d/google-chrome.repo
sudo yum -y install git nano wget bzip2 gcc libX11 libX11-devel xclock xorg-x11-drivers xorg-x11-docs xorg-x11-xinit unzip google-chrome-stable

#Installation of conda and conda packages
function conda_install(){
	#Install the Miniconda Python pachages manager
	#As is is a complex procedure, it is packed in a function. If you need to re-run this script without reinstalling Anaconda,
	#comment out the conda_install() function call several lines below.
	conda_home=/srv/conda
	python_version=3
	echo "Next, the Miniconda package will be downloaded and installed"
	wget https://repo.continuum.io/miniconda/Miniconda${python_version}-latest-Linux-x86_64.sh
	chmod +x Miniconda${python_version}-latest-Linux-x86_64.sh
	echo "You should install Miniconda to the default path there appears"
	sudo sh Miniconda${python_version}-latest-Linux-x86_64.sh -p ${conda_home} -u -b
	rm Miniconda${python_version}-latest-Linux-x86_64.sh
	#Make the updated shell path available in this session:
	export PATH="$PATH:${conda_home}"
    conda_env='base'
    source ${conda_home}/bin/activate ${conda_env}
}
condabin=`which conda &> /dev/null`
if [ -z $condabin ]
then
	conda_home=/srv/conda
	conda_install
else 
    conda_home=${condabin%/bin/conda}
    echo "Conda installation found at $conda_home. Script will use that installation."
fi
conda_env='python37'
source ${conda_home}/bin/activate ${conda_env} && echo Activated conda environment ${conda_env} || ( \
    #Conda environment not found: creating it
    ${conda_home}/bin/conda create -n ${conda_env} python=3.7; \
    source ${conda_home}/bin/activate ${conda_env}; \
    echo Created and activated the conda environment ${conda_env} )
#echo copref ${CONDA_PREFIX}
#source activate base
env_preffix=${conda_home}/envs/python37
sudo ${conda_home}/bin/conda install -y -n ${conda_env} -c bioconda numpy pandas pysam
sudo ${conda_home}/bin/conda install -y -n ${conda_env} -c conda-forge mechanicalsoup selenium
sudo ${conda_home}/bin/conda install -y -n ${conda_env} pymongo flask cython lxml requests
sudo ${env_preffix}/bin/pip install -U pip
sudo ${env_preffix}/bin/pip install flask-runner flask-errormail sendgrid
#Gnuplot installation
gpplace=$(which gnuplot) &>/dev/null && echo "Gnuplot was found at $gpplace; using that gnuplot" || (
    echo "Installing gnuplot..."; wget https://cytranet.dl.sourceforge.net/project/gnuplot/gnuplot/5.2.4/gnuplot-5.2.4.tar.gz; \
	tar -xvzf gnuplot-5.2.4.tar.gz; cd gnuplot-5.2.4; ./configure; make; sudo make install; \
	#make check; \
	cd ..; sudo rm -rf gnuplot-5.2.4* ) 

#Chrome driver (For Selenium)
wget https://chromedriver.storage.googleapis.com/2.40/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin

#echo "Now you are in the folder `pwd`"
echo "To run PM1_plotter, you first need to activate the ${conda_env} environment, using the command source ${conda_home}/bin/activate ${conda_env}."
echo "Then, you should change to the directory /srv/qgen/snippets/PM1_plots. On this directory, you may execute the PM1_plotter script using, "\
"for example, the code 'python PM1_plotter.py ABCC8 123 -i' (for the ABCC1 gene, main position 123, and where the -i stands for interactive graph)"
