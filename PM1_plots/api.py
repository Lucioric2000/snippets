import requests, json, sys, re, time, mechanicalsoup, fnmatch, traceback, sendgrid, base64
from sendgrid.helpers.mail import Email, Content, Mail, Attachment
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.remote.command import Command
chrome_options=webdriver.ChromeOptions()
chrome_options.set_headless(True)
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument('--disable-gpu')  # applicable to windows os only
chrome_options.add_argument("--disable-extensions")
chrome_options.add_experimental_option(
            'prefs', {
                'download.default_directory': "/tmp",
                'download.prompt_for_download': False,
                'download.directory_upgrade': True,
                'safebrowsing.enabled': True
            }
        )
chrome_driver = webdriver.Chrome(chrome_options=chrome_options)#,executable_path="/usr/local/bin")
chrome_driver.set_script_timeout(30)


class Uniprot_api():

    def __init__(self):
        self.upload_ext = 'https://www.uniprot.org/uploadlists/'
        self.entry_ext = 'https://www.uniprot.org/uniprot/'

    #given an ensembl_id returns the uniprot responses as a list of dictionaries
    def get_pid_from_gene(self, ensembl_id):
        params = {'from':'ENSEMBL_ID','to':'ACC','format':'tab','query': ensembl_id }
        r = requests.get(self.upload_ext, params=params)
        dict_entry_list = []
        split_r = r.text.split('\n')
        headers = split_r[0].split('\t')
        for entry in split_r:
            if entry:
                entry_list = entry.split('\t')
                if entry_list != headers:
                    dict_entry_list.append(dict(zip(headers, entry_list)))
        with open("save/ensembl_{0}.html".format(ensembl_id),"w") as opf:
            opf.write(r.text)
        return dict_entry_list
    #Return the Uniprot info from a previously saved file
    def get_pid_from_file(self, filename):
        #params = {'from':'ENSEMBL_ID','to':'ACC','format':'tab','query': ensembl_id }
        #r = requests.get(self.upload_ext, params=params)
        with open(filename,"r") as opf:
            fileread=opf.read()
        dict_entry_list = []
        split_r = fileread.split('\n')
        headers = split_r[0].split('\t')
        for entry in split_r:
            if entry:
                entry_list = entry.split('\t')
                if entry_list != headers:
                    dict_entry_list.append(dict(zip(headers, entry_list)))
        return dict_entry_list

    def get_entry_gff(self, pid):
        r = requests.get(self.entry_ext + str(pid) + '.gff')
        return r

    def parse_gff(self, gff_response, required_list): 
        gff_objects = []
        gff_list = gff_response.split('\n')
        for annotation in gff_list:
            spl_anno = annotation.split('\t')
            if spl_anno != [''] and '#' not in spl_anno[0]:
                if spl_anno[2] in required_list:
                    gff_objects.append(Gff_object(spl_anno))
        return gff_objects  

class Gff_object():
  
    def __init__(self, gff_line):
        self.ID = gff_line[0]
        self.db_annotation = gff_line[1]
        self.anno_type = gff_line[2]
        self.start = gff_line[3]
        self.stop = gff_line[4]
    def __repr__(self):
        return f"<{self.__class__.__name__} for {self.db_annotation} {self.ID} {self.start}:{self.stop}, is a {self.anno_type}>"

class Ensembl_api():

    def __init__(self):
        self.server = "http://grch37.rest.ensembl.org/"

    #returns ensembl id from HGNC gene symbol
    def query_HGNC(self, gene_symbol):
        ext = "/xrefs/symbol/homo_sapiens/" + gene_symbol + "?external_db=HGNC"
        r = requests.get(self.server + ext, headers={ "Content-Type" : "application/json"})    
        json_r = r.json()
        for transcript in json_r:
            if "ENST" in transcript["id"]:              
                print("Ensembl Transcript ID: "+ transcript["id"])
        for reference in json_r:
            if "ENSG" in reference["id"]:              
                print("Ensembl Gene ID for " + gene_symbol + ": " + reference["id"] + "\n")
                return reference["id"]
                
    def tester(self, string):
        print(string)

def jsonloads_from_html(request):
    """As sometimes, although the page is requested with the headers Content-type:text/json, the page is rendered as a
    HTML document"""
    try:
        jsondict=request.json()
    except json.decoder.JSONDecodeError as jsondecerr:
        bs=BeautifulSoup(request.text,"html.parser")
        scripts=bs.find_all("script")
        jsondict={}
        for script in scripts:
            if script.string is None:
                continue
            assert len(script.contents)==1
            chrome_driver.execute_script(script.contents[0])
            jsondict=chrome_driver.execute_script("return {'gene':gene,'transcript':transcript};")
            return jsondict#For now only parse the first script tag
    return jsondict
                
class Exac_api():

    def __init__(self):
        #self.server = "http://exac.hms.harvard.edu/"
        self.server = "http://exac.broadinstitute.org"
        self.json_headers = {"Content-Type" : "application/json"}

    def variants_in_gene(self, ensembl_id):
        #ext = "/rest/gene/variants_in_gene/" + ensembl_id
        ext = "/gene/" + ensembl_id
        #ext = "/gene/variants_in_gene/" + ensembl_id
        r = requests.get(self.server + ext, headers=self.json_headers)
        texto=chrome_driver.execute(Command.GET,{"url":self.server + ext,"headers":self.json_headers})

        json_r=jsonloads_from_html(r)
        return json_r
    
    def canonical_transcript(self, ensembl_id):
        #ext = "/rest/gene/" + ensembl_id
        ext = "/gene/" + ensembl_id
        r = requests.get(self.server + ext, headers=self.json_headers)
        #json_r = r.json()
        json_r=jsonloads_from_html(r)
        return json_r

    def variants_in_region(self, chr, start, stop):
        ext = "/rest/region/variants_in_region/" + chr + '-' + start + '-' + stop
        r = requests.get(self.server + ext, headers=self.json_headers)
        #json_r = r.json()
        json_r=jsonloads_from_html(r)
        return json_r

    # update each variant entry with het_count and hemi_count(where applicable)
    def update_variant(self, variant_list):
        for variant in variant_list:
            try:
                variant['het_count'] = variant["allele_count"]-(variant["hom_count"]+variant["hemi_count"])
                variant['hemi_freq'] = variant['hemi_count']/variant['allele_num']
                variant['het_freq'] = variant['het_count']/variant['allele_num'] 
                try:
                    variant['hom_freq'] = variant['hom_count']/variant['allele_num']
                except:
                    pass
            except:
                variant['het_count'] = variant["allele_count"]-variant["hom_count"]
                variant['het_freq'] = variant['het_count']/variant['allele_num'] 
                variant['hom_freq'] = variant['hom_count']/variant['allele_num']
        return variant_list

    #filters variants in gene with a given key and value. keep or remove option
    def filter_variants(self, variant_list, key, value, remove=False):
        pass_vars = []
        for variant in variant_list:
            if remove == False:
                #print("ky",key,variant,value,variant_list.keys())
                if key=="filter" and value=="PASS":
                    #assert 0,(variant,variant_list)
                    pass_vars.append(variant_list[variant])
                elif key=="CANONICAL" and value=="YES":
                    if "canonical_transcript" in variant:
                        if variant["canonical_transcript"]==variant["gene_id"]:
                            pass_vars.append(variant)
                elif variant[key] == value:
                    pass_vars.append(variant)
            #only keeps those not meeting the criteria
            else:
                print("ky2",key,value,variant,variant_list)
                if variant[key] == value:
                    pass
                else:
                    pass_vars.append(variant)
        return pass_vars

    #provide the starting list and dict {key : value} for each to be filtered.
    def filter_by_dict(self, starting_list, filter_dict):
        iteration_list = []
        count = 0
        for k,v in filter_dict.items():
            for variant_type in v:
                if count == 0:
                    this_filter = self.filter_variants(starting_list, k, variant_type, remove=True)
                    iteration_list.append(this_filter)
                    count += 1
                elif count > 0:
                    this_filter = self.filter_variants(iteration_list[-1], k, variant_type, remove=True)
                    iteration_list.append(this_filter)
        return iteration_list[-1]

    def position_frequency(self, var_list, hom=False, hemi=False):
        if hom==True:
            var_freq_pos_dict = self.dict_extractor('hom_freq', 'hom_pos', var_list, hom=True)
        elif hemi==True:
            var_freq_pos_dict = self.dict_extractor('hemi_freq', 'hemi_pos', var_list, hemi=True)
        else:
            var_freq_pos_dict = self.dict_extractor('het_freq', 'het_pos', var_list)
        return var_freq_pos_dict

    def dict_extractor(self, freq_key, pos_key, var_list, hom=False, hemi=False):
        freq_pos = { freq_key : [],
                     pos_key : []}
        for variant_dict in var_list:
            if hom==True:
                freq_pos[freq_key].append(variant_dict["hom_freq"])
            elif hemi==True:
                freq_pos[freq_key].append(variant_dict["hemi_freq"])
            else:
                freq_pos[freq_key].append(variant_dict["het_freq"])
            freq_pos[pos_key].append(self.extract_protein_position(variant_dict["HGVSp"]))
        return freq_pos


    #takes protein position from HGVS protein nomenclature for syn/miss
    def extract_protein_position(self, HGVSp):
        m = re.search(r'(p\.)([^0-9]*)(\d{1,})(.*)', HGVSp)
        #if matches returns the format
        if m:
            return m.group(3)
        else:
            return HGVSp

#creates class based on key, value **kwargs
class HGMD_variant():
    def __init__(self, **entries):
        self.__dict__.update(entries)

class HGMD_pro():

    #could make the object the login and methods what to do after
    def __init__(self, gene_name):
        self.gene = gene_name

    def scrape_HGMD_all_mutations(self,hgmd_username,hgmd_password):
        browser = mechanicalsoup.Browser()
        login_page = browser.get("http://portal.biobase-international.com/cgi-bin/portal/login.cgi")
        time.sleep(2)
        login_form = mechanicalsoup.Form(login_page.soup.select_one('#login_form'))
        time.sleep(2)
        # login username and user_password required as strings
        redirect_url=redirect_url="/hgmd/pro/gene.php?gene=" + self.gene
        login_form.input({"login" : hgmd_username, "password" : hgmd_password, "redirect_url":redirect_url})
        time.sleep(2)
        r = browser.submit(login_form, login_page.url)
        time.sleep(2)
        soup = self.form_finder(browser, self.gene)
        return soup
    def log_and_email_htmls_with_error(self,htmls,error,subject):
        #SenfGrid Key for sengding mails with debug info to me
        sendgrid_key="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"
        sg = sendgrid.SendGridAPIClient(apikey=sendgrid_key)
        from_email = Email("lucioric@ibt.unam.mx")
        to_email = Email("lucioric@ibt.unam.mx")
        #from_email = Email("lucioric@freelancecuernavaca.com")
        #to_email = Email("lucioric@freelancecuernavaca.com")
        contentstr="{0}. During the analysis, the following error happened: {1}".format(subject,traceback.format_exc())
        content = Content("text/plain", contentstr)
        mail = Mail(from_email, subject, to_email, content)
        error_log_h=open("error.log","a")
        error_log_h.write("Error at {0}:\n".format(time.asctime()))
        error_log_h.write(contentstr)
        error_log_h.write("\n")
        print("HTML code of the web page got was dumped in the file error.log")
        for (htmlname,htmlcontents) in htmls.items():
            att=Attachment()
            error_log_h.write("html {0}:\n{1}\n".format(htmlname,htmlcontents))
            if isinstance(htmlcontents,str):
                htmlcontents=htmlcontents.encode("UTF-8")
            att.content=base64.b64encode(htmlcontents).decode()
            att.type="text/html"
            att.filename=htmlname
            att.disposition="attachment"
            mail.add_attachment(att)
        response = sg.client.mail.send.post(request_body=mail.get())
        error_log_h.write("mail sending status: {0}\n".format(response))
        error_log_h.write("mail sending status code: {0}\n".format(response.status_code))
        error_log_h.write("mail sending status body: {0}\n".format(response.body))
        error_log_h.write("======================\n")
        error_log_h.close()
    def email_html_for_development(self,html,subject,gene):
        #SenfGrid Key for sengding mails with debug info to me
        sendgrid_key="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"
        sg = sendgrid.SendGridAPIClient(apikey=sendgrid_key)
        from_email = Email("lucioric@ibt.unam.mx")
        to_email = Email("lucioric@ibt.unam.mx")
        contentstr="{0}. The gene getting was successful".format(subject)
        content = Content("text/plain", contentstr)
        mail = Mail(from_email, subject, to_email, content)
        att=Attachment()
        if isinstance(html,str):
            html=html.encode("UTF-8")
        att.content=base64.b64encode(html).decode()
        att.type="text/html"
        att.filename="HGMD_{0}.html".format(gene)
        att.disposition="attachment"
        mail.add_attachment(att)
        response = sg.client.mail.send.post(request_body=mail.get())

      
    def form_finder(self, browser, gene):
        gene_search = browser.get("https://portal.biobase-international.com/hgmd/pro/gene.php?gene=" + gene)
        time.sleep(0.5)
        soup = BeautifulSoup(gene_search.content,features="lxml")
        form = soup.find("form", attrs={ "action" : "all.php" })
        if form is None:
            gene_search_2=browser.get("https://portal.biobase-international.com/cgi-bin/portal/login.cgi?redirect_url=/hgmd/pro/gene.php?gene=" + gene)
            time.sleep(0.5)
            soup = BeautifulSoup(gene_search_2.content,features="lxml")
            form = soup.find("form", attrs={ "action" : "all.php" })
        try:
            gene_id_element = form.find("input", attrs={"name" : "gene_id"})
        except AttributeError as exc:
            if exc.args==("'NoneType' object has no attribute 'find'",):
                htmls={"gene_search_{0}.html".format(gene):gene_search.content,"soup_{0}.html".format(gene):str(soup)}
                subject = "PM1_plotter Error: Gene page {0} for debug".format(gene)
                print("\nHGMD exception executed:")
                print("Check HGMD username and password are correct and try again.\nAlternatively check you are not already logged in to HGMD with a web browser:\nhttps://portal.biobase-international.com/cgi-bin/portal/login.cgi\n")
                #print("HTML code of the web page got was dumped in the file error.log")
                self.log_and_email_htmls_with_error(htmls,exc,subject)
                sys.exit()
                #return None
            else:
                htmls={"gene_search_{0}.html".format(gene):gene_search.content,"soup_{0}.html".format(gene):str(soup)}
                subject = "PM1_plotter Error: Gene page {0} for debug".format(gene)
                print("\nThe following execption occured while executing the HGMD results HTML: {0}".format(traceback.format_exc()))
                #print("HTML code dumped in the file error.log")
                self.log_and_email_htmls_with_error(htmls,exc,subject)
                raise exc
        except Exception as exc:
            htmls={"gene_search_{0}.html".format(gene):gene_search.content,"soup_{0}.html".format(gene):str(soup)}
            subject = "PM1_plotter Error: Gene page {0} for debug".format(gene)
            print("\nThe following execption occured while executing the HGMD results HTML: {0}".format(traceback.format_exc()))
            #print("HTML code dumped in the file error.log")
            self.log_and_email_htmls_with_error(htmls,exc,subject)
            raise exc
        gene_id_value = gene_id_element['value']
        trans_element = form.find("input", attrs={"name" : "refcore"})
        HGMD_transcript_id = trans_element['value']
        print("HGMD transcript ID: " + HGMD_transcript_id)     
        params = {"gene" : self.gene, "inclsnp" : "N", "base" : "Z", "refcore" : HGMD_transcript_id, "gene_id" : gene_id_value, "database" : "Get all mutations"}
        url = "https://portal.biobase-international.com/hgmd/pro/all.php"
        response = browser.post(url, data=params)
        time.sleep(0.5)
        soup = BeautifulSoup(response.content,features="lxml")
        self.email_html_for_development(soup,"PM1_plotter: Gene page {0} for debug".format(gene),gene)
        response.close()
        return soup
        
        ###################################remember to un comment the above######################################################################
        
    def extract_missense(self, all_mutations_soup):
    	#may need to add "HGMD accession" header to headers when it's live
        HGMD_headers = ["HGMD_codon_change", "amino_acid_change", "HGVS_nuc", "HGVS_prot", "var_class", "phenotype","reference", "additional"]
        HGMD_headers_legacy = ["HGMD_codon_change", "amino_acid_change", "legacy_change", "HGVS_nuc", "HGVS_prot", "var_class", "phenotype","reference", "additional"]
        HGMD_var_objs = []
        soup = all_mutations_soup
        #soup = BeautifulSoup(open("html_to_parse"), "html.parser")
        table = soup.find("table", attrs={ "class" : "gene" })
        rows = table.find_all('tr')
        num_rows = 0
        for row in rows:
            cols = row.findAll("td")
            cols = [ele.text.strip() for ele in cols]
            #remove empty strings
            cols = [ele for ele in cols if ele]
            # search through each entry to find nonsense mutations and remove these from final list
            regex = re.compile('p.[A-Z]{1}[0-9]+\*')
            matches = [string for string in cols if re.match(regex, string)]
            if matches == []:
                if len(cols) == 8:
                    variant_dict = {key:value for key,value in zip(HGMD_headers, cols)}
                    var_instance = HGMD_variant(**variant_dict)
                    HGMD_var_objs.append(var_instance)
                elif len(cols) == 9: # if a legacy naming column exists, for example gene INSR
                    variant_dict = {key:value for key,value in zip(HGMD_headers_legacy, cols)}
                    var_instance = HGMD_variant(**variant_dict)
                    HGMD_var_objs.append(var_instance)
                elif len(cols) == 7:
                    variant_dict = {key:value for key,value in zip(HGMD_headers, cols)}
                    if 'additional' not in variant_dict:
                        variant_dict['additional'] = 'None'
                    elif additional in variant_dict:
                        continue
                    var_instance = HGMD_variant(**variant_dict)
                    HGMD_var_objs.append(var_instance)
                else:
                    if num_rows != 0:
                        print("Columns in HGMD table = " + str(len(cols)) + ". Cannot handle this many columns")
                num_rows =+1
            else:
                pass
        return HGMD_var_objs

    def write_DM_file(self, variant_instance_list):
        with open("temp_hgmd_file", 'w') as ouf:
            for item in variant_instance_list:
                try:
                    m = re.search(r'(p\.)([^0-9]*)(\d{1,})(.*)', item.hgvs_prot)
                    if m:
                        print(item.variant_class)
                        if item.variant_class == "DM":
                            string = m.group(3) + '\t' + '1\n'
                        elif item.variant_class == "DM?":
                            string = m.group(3) + '\t' + '\t' + '2\n'
                        else:
                            string = m.group(3) + '\t' + '\t' + '\t' + '3\n'
                        ouf.write(string)
                    else:
                    	print("not_m " + item.hgvs_prot)
                except:
                    pass
        return "temp_hgmd_file"



if __name__ == "__main__":
    Ex = Exac_api()
    variants_in_gene_json = Ex.variants_in_gene("ENSG00000077279")
    print(variants_in_gene_json)

