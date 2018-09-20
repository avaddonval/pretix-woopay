FROM pretix/standalone:stable
USER root
RUN export PYTHONPATH=$PYTHONPATH:/pretix/src && pip3 install git+https://github.com/avaddonval/pretix-onepay.git@master
USER pretixuser
RUN cd /pretix/src && make production
