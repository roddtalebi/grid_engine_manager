'''
from john turgesson:
https://eoslcm.gtri.gatech.edu/confluence/pages/viewpage.action?spaceKey=TMTPROJ&title=AATTC+Design

after taking some time to brainstorm and draft/whiteboard conceptually, going to try to translate that into code + pseudocode.

the goal of this is to clarify WHAT the regulator does and HOW.
'''

### packages
import os
import sys
import xml.etree.ElementTree as ET
from lxml import etree


### local modules
import emade
import pyGTMOEA
import charlie_work
import tmt_manager # some custom module to handle all the tmt stuff?



class Regulator():
    '''
    in my head, the regulator starts and stops the whole optimization process flow.
    ...it is both the heart pumping blood to everything else but it is also the brain making informed decisions and sending instructions.

    so our main program would create an instance of a Regulator and call some Regulator.run() method to start the optimization.
    this means that the Regulator instance would carry all the parameters for the optimization likely fed in my some xml?
    '''
    def __init__(self, optimization_params_xml):
        '''
        read in some config xml file listing out all the params for our optimization:
         * whole population size
         * genome seeds
         * evolutionary params for charlie_work, pyGTMOEA, emade
         * tmt params for creating + submitting matricies
        '''
        # Load in global params for everything
        self.load_xml(optimization_params_xml)

        # Initialize the Evolutionary-Machines with their params digested by self.load_xml()
        self.emade = emade.emade(**self.emade_configs_dict)
        self.pyGTMOEA = pyGTMOEA.pyGTMOEA(**self.pyGTMOEA_configs_dict)
        self.charlie_work = charlie_work.optimization(**self.charlie_work_configs_dict)

        # Genome seeding; or does that happen in previous step?
        do

        # something with tmt? or all that handled with self.load_xml()
        # i guess as long as we know which MatrixType to use and know how to fill out matrix then we're good.

        self.optimize = False # on/off switch to be turned on later
        self.generation = 0

        return



    def load_params_xml(self, xml_file):
        '''
        taken from emade
        https://github.gatech.edu/emade/emade/blob/CacheV2/src/GPFramework/launchEMADE.py
        '''
        # TODO
        SOME_SCHEMA_FILE = ""

        # Valid XML file with inputSchema.xsd using lxml.etree
        schema_doc = etree.parse(os.path.join(SOME_SCHEMA_FILE))
        schema = etree.XMLSchema(schema_doc)

        doc = etree.parse(xml_file)
        # Raise error if invalid XML
        try:
            schema.assertValid(doc)
        except:
            raise

        # Uses xml.etree.ElementTree to parse the XML
        tree = ET.parse(xml_file)
        root = tree.getroot()


        # then for a specific set of configs, in emade they call some other function that parses root
        #...something like:
        params_dict = {}
        some_param = root.find('someParam')
        paramsList = root.iter('someListTag')
        for i, paramTag in enumerate(paramsList):
            params_dict[i] = {'name': paramTag.findtext('name'),
                              'other': paramTag.findtext('other')}
            # or instead of assigning to a dict, just assign to self or make a specific class that can be init from paramTag
            self.__dict__['param_%i' % i] = params_dict[i]


    def run_single_generation(self, population=None):
        '''
        not sure how it will happen but here we want to get each evo-machine to perform a single evolution/generation and grab the offspring.
        then we want some way to store all the individuals...make a population class? include some hall of fame?
        '''
        if population is not None:
            # have some way to seed each evo-machine with the evaluated individuals from previous generation
            do


        evolution_tracker = {}
        sub_population = self.emade.run_single_generation()
        for indiv in sub_population:
            evolution_tracker[indiv.id] = "emade"
            # OR
            population.append( FlarePattern(indiv, generation=self.generation, evo_machine="emade"))

        sub_population += self.pyGTMOEA.run_single_generation()
        sub_population += self.charlie_work.run_single_generation()

        return population


    def fill_testMatrixInstance(self, flare_patterns):
        '''
        I assume that self will have a bunch of the misc dims/config needed to fill out the matrix outside of the 
        flare patterns we want to test.
        and assuming that flare patterns is already in some form digestable/expected by tmt and just a list of them to make a config for each...or not?
        '''
        pass

        unique_test_matrix_name = ""
        with open(unique_test_matrix_name, 'w') as f:
            f.write("stuff\n")

        return unique_test_matrix_name


    def run_tmt(self, test_matrix_xmlfile):
        '''
        someway to interface with tmt to:
        * submit a matrix
        * track it's progress
        * return performance and assign back to the correct flare pattern
        '''
        pass


    def population_selection(self):
        '''
        idk. something from deap.tools i guess
        '''
        pass


    def check_termination_condition(self):
        '''
        when do we want to stop optimization?
        '''
        if terminate:
            self.optimize = False


    def run_optimization(self):
        '''
        basically do everything important here

        it is assumed that the evo-machines already have their population seeds from the self.__init__() step
        '''
        # Start initial evolution from seeds or from scratch
        self.optimize = True
        self.generation = 1
        population = self.run_single_generation()

        # whatever, we're left with a list of flare_patterns in population we want to test
        test_matrix_xmlfile = self.fill_testMatrixInstance(population)

        # submit matrix to be run and figure out when to stop and grab results
        self.run_tmt(test_matrix_xmlfile)

        # now that we have evaluated all the flare patterns, do population selection
        self.population_selection(population)
        self.check_termination_conditions(population)

        # use the reduced population to seed the 3 evo-machines for the next generation
        # this is where the loop will start
        while self.optimize:
            generation+=1
            population = self.run_single_generation(population)
            test_matrix_xmlfile = self.fill_testMatrixInstance(population)
            self.run_tmt(test_matrix_xmlfile)
            self.population_selection(population)
            self.check_termination_conditions(population)




class FlarePattern():
    '''
    these are how we represent individuals in the optimization

    not married to it, but could be an easy way to keep track of metadata attached to a flare pattern:
    * which evo machine spawned it
    * which generation
    * fitness scores
    ...basically anything normally captured by an evo-machine but isn't captured because of the interupted evolution that occurs
    '''
    def __init__(self, pattern, **kwargs):
        self.pattern = pattern
        self.__dict__.update(kwargs)
        # maybe produce some unique id from the pattern?
        self.id = hex('something unique')



class Population():
    '''
    maybe this will be a convenient way to keep track of population?
    '''
    def __init__(self):
        self.population = []
        self.hall_of_fame = []

    def __getitem__(self, index):
        return self.population[index]