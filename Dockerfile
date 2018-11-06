FROM centos:centos7.3.1611
MAINTAINER lucioric2000@hotmail.com

RUN yum -y install sudo applydeltarpm
ADD PM1_plots/installPM1.bash /srv/installPM1.bash
RUN chmod +x /srv/installPM1.bash
RUN cd /srv; ./installPM1.bash
RUN /srv/conda/bin/conda info --envs
RUN source /srv/conda/bin/activate python37
RUN cd /srv/qgen/snippets/PM1_plots; python PM1_plotter.py
