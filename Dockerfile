FROM centos:centos7.3.1611
MAINTAINER lucioric2000@hotmail.com
RUN echo 2
RUN yum -y install sudo applydeltarpm
RUN echo 3
ADD PM1_plots/installPM1.bash /srv/installPM1.bash
RUN chmod +x /srv/installPM1.bash
RUN cd /srv; ./installPM1.bash
RUN cd /srv/qgen/snippets/PM1_plots; source /srv/conda/bin/activate python37; /srv/conda/bin/conda info --envs
RUN cd /srv/qgen/snippets/PM1_plots; source /srv/conda/bin/activate python37; which python
RUN cd /srv/qgen/snippets/PM1_plots; source /srv/conda/bin/activate python37; python PM1_plotter.py
