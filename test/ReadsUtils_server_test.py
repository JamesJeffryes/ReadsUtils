import unittest
import time

from os import environ
import shutil
import os
from DataFileUtil.DataFileUtilClient import DataFileUtil
import requests
from pprint import pprint
import subprocess
import hashlib
import inspect
try:
    from ConfigParser import ConfigParser  # py2 @UnusedImport
except:
    from configparser import ConfigParser  # py3 @UnresolvedImport @Reimport

from Workspace.WorkspaceClient import Workspace
from biokbase.AbstractHandle.Client import AbstractHandle as HandleService  # @UnresolvedImport @IgnorePep8
from DataFileUtil.baseclient import ServerError as DFUError
from ReadsUtils.ReadsUtilsImpl import ReadsUtils
from ReadsUtils.ReadsUtilsServer import MethodContext

# TODO update the uploader tests to use the infrastructure for the downloader tests @IgnorePep8


class TestError(Exception):
    pass


def dictmerge(x, y):
    z = x.copy()
    z.update(y)
    return z


class ReadsUtilsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = environ.get('KB_AUTH_TOKEN', None)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': cls.token,
                        'provenance': [
                            {'service': 'ReadsUtils',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('ReadsUtils'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.shockURL = cls.cfg['shock-url']
        cls.ws = Workspace(cls.cfg['workspace-url'], token=cls.token)
        cls.hs = HandleService(url=cls.cfg['handle-service-url'],
                               token=cls.token)
        cls.impl = ReadsUtils(cls.cfg)
        shutil.rmtree(cls.cfg['scratch'])
        os.mkdir(cls.cfg['scratch'])
        suffix = int(time.time() * 1000)
        wsName = "test_ReadsUtils_" + str(suffix)
        cls.ws_info = cls.ws.create_workspace({'workspace': wsName})
        cls.dfu = DataFileUtil(os.environ['SDK_CALLBACK_URL'], token=cls.token)
        cls.staged = {}
        cls.nodes_to_delete = []
        cls.handles_to_delete = []
        cls.setupTestData()
        print('\n\n=============== Starting tests ==================')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'ws_info'):
            cls.ws.delete_workspace({'id': cls.ws_info[0]})
            print('Deleted test workspace')
        if hasattr(cls, 'nodes_to_delete'):
            for node in cls.nodes_to_delete:
                cls.delete_shock_node(node)
        if hasattr(cls, 'handles_to_delete'):
            cls.hs.delete_handles(cls.hs.ids_to_handles(cls.handles_to_delete))
            print('Deleted handles ' + str(cls.handles_to_delete))

    @classmethod
    def getWsName(cls):
        return cls.ws_info[1]

    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.token)}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
        print('Deleted shock node ' + node_id)

    @classmethod
    def upload_file_to_shock(cls, file_path):
        """
        Use HTTP multi-part POST to save a file to a SHOCK instance.
        """

        header = dict()
        header["Authorization"] = "Oauth {0}".format(cls.token)

        if file_path is None:
            raise Exception("No file given for upload to SHOCK!")

        with open(os.path.abspath(file_path), 'rb') as dataFile:
            files = {'upload': dataFile}
            print('POSTing data')
            response = requests.post(
                cls.shockURL + '/node', headers=header, files=files,
                stream=True, allow_redirects=True)
            print('got response')

        if not response.ok:
            response.raise_for_status()

        result = response.json()

        if result['error']:
            raise Exception(result['error'][0])
        else:
            return result["data"]

    @classmethod
    def upload_file_to_shock_and_get_handle(cls, test_file):
        '''
        Uploads the file in test_file to shock and returns the node and a
        handle to the node.
        '''
        print('loading file to shock: ' + test_file)
        node = cls.upload_file_to_shock(test_file)
        pprint(node)
        cls.nodes_to_delete.append(node['id'])

        print('creating handle for shock id ' + node['id'])
        handle_id = cls.hs.persist_handle({'id': node['id'],
                                           'type': 'shock',
                                           'url': cls.shockURL
                                           })
        cls.handles_to_delete.append(handle_id)

        md5 = node['file']['checksum']['md5']
        return node['id'], handle_id, md5, node['file']['size']

    @classmethod
    def upload_assembly(cls, wsobjname, object_body, fwd_reads,
                        rev_reads=None, kbase_assy=False, single_end=False):
        if single_end and rev_reads:
            raise ValueError('u r supr dum')

        print('\n===============staging data for object ' + wsobjname +
              '================')
        print('uploading forward reads file ' + fwd_reads['file'])
        fwd_id, fwd_handle_id, fwd_md5, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(fwd_reads['file'])
        fwd_handle = {
                      'hid': fwd_handle_id,
                      'file_name': fwd_reads['name'],
                      'id': fwd_id,
                      'url': cls.shockURL,
                      'type': 'shock',
                      'remote_md5': fwd_md5
                      }

        ob = dict(object_body)  # copy
        if kbase_assy:
            if single_end:
                wstype = 'KBaseAssembly.SingleEndLibrary'
                ob['handle'] = fwd_handle
            else:
                wstype = 'KBaseAssembly.PairedEndLibrary'
                ob['handle_1'] = fwd_handle
        else:
            if single_end:
                wstype = 'KBaseFile.SingleEndLibrary'
                obkey = 'lib'
            else:
                wstype = 'KBaseFile.PairedEndLibrary'
                obkey = 'lib1'
            ob[obkey] = \
                {'file': fwd_handle,
                 'encoding': 'UTF8',
                 'type': fwd_reads['type'],
                 'size': fwd_size
                 }

        rev_id = None
        if rev_reads:
            print('uploading reverse reads file ' + rev_reads['file'])
            rev_id, rev_handle_id, rev_md5, rev_size = \
                cls.upload_file_to_shock_and_get_handle(rev_reads['file'])
            rev_handle = {
                          'hid': rev_handle_id,
                          'file_name': rev_reads['name'],
                          'id': rev_id,
                          'url': cls.shockURL,
                          'type': 'shock',
                          'remote_md5': rev_md5
                          }
            if kbase_assy:
                ob['handle_2'] = rev_handle
            else:
                ob['lib2'] = \
                    {'file': rev_handle,
                     'encoding': 'UTF8',
                     'type': rev_reads['type'],
                     'size': rev_size
                     }

        print('Saving object data')
        objdata = cls.save_ws_obj(ob, wsobjname, wstype)
        print('Saved object: ')
        pprint(objdata)
        pprint(ob)
        cls.staged[wsobjname] = {'info': objdata,
                                 'ref': cls.make_ref(objdata),
                                 'fwd_node_id': fwd_id,
                                 'rev_node_id': rev_id
                                 }

    @classmethod
    def upload_file_ref(cls, wsobjname, file_):
        fwd_id, fwd_handle_id, fwd_md5, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(file_)
        ob = {'file': {'hid': fwd_handle_id,
                       'file_name': file_,
                       'id': fwd_id,
                       'url': cls.shockURL,
                       'type': 'shock',
                       'remote_md5': fwd_md5
                       },
              'encoding': 'UTF8',
              'type': 'stuff',
              'size': fwd_size
              }
        info = cls.save_ws_obj(ob, wsobjname, 'KBaseFile.FileRef')
        cls.staged[wsobjname] = {'info': info,
                                 'ref': cls.make_ref(info)}

    @classmethod
    def upload_empty_data(cls, wsobjname):
        info = cls.save_ws_obj({}, wsobjname, 'Empty.AType')
        cls.staged[wsobjname] = {'info': info,
                                 'ref': cls.make_ref(info)}

    @classmethod
    def save_ws_obj(cls, obj, objname, objtype):
        return cls.ws.save_objects({
            'workspace': cls.getWsName(),
            'objects': [{'type': objtype,
                         'data': obj,
                         'name': objname
                         }]
            })[0]

    @classmethod
    def gzip(cls, *files):
        for f in files:
            if subprocess.call(['gzip', '-f', '-k', f]):
                raise TestError(
                    'Error zipping file {}'.format(f))

    @classmethod
    def setupTestData(cls):
        print('Shock url ' + cls.shockURL)
        print('WS url ' + cls.ws._client.url)
        print('Handle service url ' + cls.hs.url)
        print('staging data')
        sq = {'sequencing_tech': 'fake data'}
        cls.gzip('data/small.forward.fq', 'data/small.reverse.fq',
                 'data/interleaved.fq')
        # get file type from type
        fwd_reads = {'file': 'data/small.forward.fq',
                     'name': 'test_fwd.fastq',
                     'type': 'fastq'}
        fwd_reads_gz = {'file': 'data/small.forward.fq.gz',
                        'name': 'test_fwd.fastq.gz',
                        'type': 'fastq.Gz'}
        # get file type from handle file name
        rev_reads = {'file': 'data/small.reverse.fq',
                     'name': 'test_rev.FQ',
                     'type': ''}
        rev_reads_gz = {'file': 'data/small.reverse.fq.gz',
                        'name': 'test_rev.FQ.gZ',
                        'type': ''}
        # get file type from shock node file name
        int_reads = {'file': 'data/interleaved.fq',
                     'name': '',
                     'type': ''}
        int_reads_gz = {'file': 'data/interleaved.fq.gz',
                        'name': '',
                        'type': ''}
        # happy path objects
        # load KBF.P int, KBF.P fr, KBF.S KBA.P int, KBA.P fr, KBA.S
        # w/wo gz
        cls.upload_assembly('frbasic', sq, fwd_reads, rev_reads=rev_reads)
        cls.upload_assembly('frbasic_gz', sq, fwd_reads_gz,
                            rev_reads=rev_reads)
        cls.upload_assembly('intbasic', sq, int_reads)
        cls.upload_assembly('intbasic_gz', sq, int_reads_gz)
        cls.upload_assembly('frbasic_kbassy', {}, fwd_reads,
                            rev_reads=rev_reads, kbase_assy=True)
        cls.upload_assembly('frbasic_kbassy_gz', {}, fwd_reads,
                            rev_reads=rev_reads_gz, kbase_assy=True)
        cls.upload_assembly('intbasic_kbassy', {}, int_reads, kbase_assy=True)
        cls.upload_assembly('intbasic_kbassy_gz', {}, int_reads_gz,
                            kbase_assy=True)
        cls.upload_assembly('single_end', sq, fwd_reads, single_end=True)
        cls.upload_assembly('single_end_gz', sq, fwd_reads_gz, single_end=True)
        cls.upload_assembly('single_end_kbassy', {}, rev_reads,
                            single_end=True, kbase_assy=True)
        cls.upload_assembly('single_end_kbassy_gz', {}, rev_reads_gz,
                            single_end=True, kbase_assy=True)

        # load objects with optional fields
        cls.upload_assembly(
            'kbassy_roo_t',
            {'insert_size_mean': 42,
             'insert_size_std_dev': 1000000,
             'read_orientation_outward': 1},
            fwd_reads, kbase_assy=True)
        cls.upload_assembly(
            'kbassy_roo_f',
            {'insert_size_mean': 43,
             'insert_size_std_dev': 1000001,
             'read_orientation_outward': 0},
            fwd_reads, kbase_assy=True)
        cls.upload_assembly(
            'kbfile_sing_sg_t',
            {'single_genome': 1,
             'strain': {'genus': 'Yersinia',
                        'species': 'pestis',
                        'strain': 'happypants'
                        },
             'source': {'source': 'my pants'},
             'sequencing_tech': 'IonTorrent',
             'read_count': 3,
             'read_size': 12,
             'gc_content': 2.3
             },
            fwd_reads, single_end=True)
        cls.upload_assembly(
            'kbfile_sing_sg_f',
            {'single_genome': 0,
             'strain': {'genus': 'Deinococcus',
                        'species': 'radiodurans',
                        'strain': 'radiopants'
                        },
             'source': {'source': 'also my pants'},
             'sequencing_tech': 'PacBio CCS',
             'read_count': 4,
             'read_size': 13,
             'gc_content': 2.4
             },
            fwd_reads, single_end=True)
        cls.upload_assembly(
            'kbfile_pe_t',
            {'single_genome': 1,
             'read_orientation_outward': 1,
             'insert_size_mean': 50,
             'insert_size_std_dev': 1000002,
             'strain': {'genus': 'Bacillus',
                        'species': 'subtilis',
                        'strain': 'soilpants'
                        },
             'source': {'source': 'my other pants'},
             'sequencing_tech': 'Sanger',
             'read_count': 5,
             'read_size': 14,
             'gc_content': 2.5
             },
            fwd_reads)
        cls.upload_assembly(
            'kbfile_pe_f',
            {'single_genome': 0,
             'read_orientation_outward': 0,
             'insert_size_mean': 51,
             'insert_size_std_dev': 1000003,
             'strain': {'genus': 'Escheria',
                        'species': 'coli',
                        'strain': 'poopypants'
                        },
             'source': {'source': 'my ex-pants'},
             'sequencing_tech': 'PacBio CLR',
             'read_count': 6,
             'read_size': 15,
             'gc_content': 2.6
             },
            fwd_reads)

        # load bad data for unhappy path testing
        shutil.copy2('data/small.forward.fq', 'data/small.forward.bad')
        bad_fn_reads = {'file': 'data/small.forward.bad',
                        'name': '',
                        'type': ''}
        cls.upload_assembly('bad_shk_name', sq, bad_fn_reads)
        bad_fn_reads['file'] = 'data/small.forward.fq'
        bad_fn_reads['name'] = 'file.terrible'
        cls.upload_assembly('bad_file_name', sq, bad_fn_reads)
        bad_fn_reads['name'] = 'small.forward.fastq'
        bad_fn_reads['type'] = 'xls'
        cls.upload_assembly('bad_file_type', sq, bad_fn_reads)
        cls.upload_assembly('bad_node', sq, fwd_reads)
        cls.delete_shock_node(cls.nodes_to_delete.pop())
        cls.upload_empty_data('empty')
        cls.upload_file_ref('fileref', 'data/small.forward.fq')
        print('Data staged.')

    @classmethod
    def make_ref(self, objinfo):
        return str(objinfo[6]) + '/' + str(objinfo[0]) + '/' + str(objinfo[4])

    def md5(self, filename):
        with open(filename, 'rb') as file_:
            hash_md5 = hashlib.md5()
            buf = file_.read(65536)
            while len(buf) > 0:
                hash_md5.update(buf)
                buf = file_.read(65536)
            return hash_md5.hexdigest()

    # MD5s not repeatable if the same file is gzipped again
    MD5_SM_F = 'e7dcea3e40d73ca0f71d11b044f30ded'
    MD5_SM_R = '2cf41e49cd6b9fdcf1e511b083bb42b5'
    MD5_SM_I = '6271cd02987c9d1c4bdc1733878fe9cf'
    MD5_FR_TO_I = '1c58d7d59c656db39cedcb431376514b'
    MD5_I_TO_F = '4a5f4c05aae26dcb288c0faec6583946'
    MD5_I_TO_R = '2be8de9afa4bcd1f437f35891363800a'

    STD_OBJ_KBF_P = {'gc_content': None,
                     'insert_size_mean': None,
                     'insert_size_std_dev': None,
                     'read_count': None,
                     'read_orientation_outward': 'false',
                     'read_size': None,
                     'sequencing_tech': u'fake data',
                     'single_genome': 'true',
                     'source': None,
                     'strain': None
                     }
    STD_OBJ_KBF_S = dictmerge(STD_OBJ_KBF_P,
                              {'read_orientation_outward': None})

    STD_OBJ_KBA = dictmerge(
        STD_OBJ_KBF_P,
        {'read_orientation_outward': None,
         'sequencing_tech': None,
         'single_genome': None
         })

    # FASTA/Q tests ########################################################

    def check_FASTA(self, filename, result):
        self.assertEqual(
            self.impl.validateFASTA(
                self.ctx, {'file_path': filename})[0]['valid'], result)

    def test_FASTA_validation(self):
        self.check_FASTA('data/sample.fa', 1)
        self.check_FASTA('data/sample.fas', 1)
        self.check_FASTA('data/sample.fna', 1)
        self.check_FASTA('data/sample.fasta', 1)
        self.check_FASTA('data/sample_missing_data.fa', 0)

    def fail_val_FASTA(self, filename, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTA(self.ctx, {'file_path': filename})
        self.assertEqual(error, str(context.exception.message))

    def fail_val_FASTQ(self, params, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTQ(self.ctx, params)
        self.assertEqual(error, str(context.exception.message))

    def test_FASTA_val_fail_no_file(self):
        self.fail_val_FASTA('nofile', 'No such file: nofile')
        self.fail_val_FASTA(None, 'No such file: None')
        self.fail_val_FASTA('', 'No such file: ')

    def test_FASTA_val_fail_bad_ext(self):
        self.fail_val_FASTA('data/sample.txt',
                            'File data/sample.txt is not a FASTA file')

    def test_FASTQ_validation(self):
        self.check_fq('data/Sample1.fastq', 0, 1)
        self.check_fq('data/Sample2_interleaved_illumina.fnq', 1, 1)
        # fail on interleaved file specified as non-interleaved
        self.check_fq('data/Sample2_interleaved_illumina.fnq', 0, 0)
        self.check_fq('data/Sample3_interleaved_casava1.8.fq', 1, 1)
        self.check_fq('data/Sample4_interleaved_NCBI_SRA.fastq', 1, 1)
        self.check_fq('data/Sample5_interleaved.fastq', 1, 1)
        self.check_fq('data/Sample5_interleaved_blank_lines.fastq', 1, 1)
        self.check_fq('data/Sample5_noninterleaved.1.fastq', 0, 1)
        self.check_fq('data/Sample5_noninterleaved.2.fastq', 0, 1)
        self.check_fq('data/Sample1_invalid.fastq', 0, 0)
        self.check_fq('data/Sample5_interleaved_missing_line.fastq', 1, 0)

    def test_FASTQ_multiple(self):
        f1 = 'data/Sample1.fastq'
        f2 = 'data/Sample4_interleaved_NCBI_SRA.fastq'
        fn1 = os.path.basename(f1)
        fn2 = os.path.basename(f2)
        nfn1 = self.cfg['scratch'] + '/' + fn1
        nfn2 = self.cfg['scratch'] + '/' + fn2
        shutil.copyfile(f1, nfn1)
        shutil.copyfile(f2, nfn2)
        self.assertEqual(self.impl.validateFASTQ(
            self.ctx, [{'file_path': nfn1,
                       'interleaved': 0},
                       {'file_path': nfn2,
                       'interleaved': 1}
                       ])[0], [{'validated': 1}, {'validated': 1}])

    def check_fq(self, filepath, interleaved, ok):
        fn = os.path.basename(filepath)
        newfn = self.cfg['scratch'] + '/' + fn
        shutil.copyfile(filepath, newfn)
        self.assertEqual(self.impl.validateFASTQ(
            self.ctx, [{'file_path': newfn,
                       'interleaved': interleaved}])[0][0]['validated'], ok)
        for l in open(newfn):
            self.assertNotEqual(l, '')

    def test_FASTQ_val_fail_no_file(self):
        self.fail_val_FASTQ([{'file_path': 'nofile'}], 'No such file: nofile')
        self.fail_val_FASTQ([{'file_path': None}], 'No such file: None')
        self.fail_val_FASTQ([{'file_path': ''}], 'No such file: ')

    def test_FASTQ_val_fail_bad_ext(self):
        self.fail_val_FASTQ([{'file_path': 'data/sample.txt'}],
                            'File data/sample.txt is not a FASTQ file')

    # Upload tests ########################################################

    def test_single_end_reads_gzip(self):
        # gzip, minimum inputs
        ret = self.upload_file_to_shock('data/Sample1.fastq.gz')
        ref = self.impl.upload_reads(self.ctx, {'fwd_id': ret['id'],
                                                'sequencing_tech': 'seqtech',
                                                'wsname': self.ws_info[1],
                                                'name': 'singlereads1'})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/singlereads1']})['data'][0]
        self.delete_shock_node(ret['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.check_lib(d['lib'], 2847, 'Sample1.fastq.gz', ret['id'],
                       '48efea6945c4382c68f5eac485c177c2')

    def test_single_end_reads_metagenome_objid(self):
        # single genome = 0, test saving to an object id
        ret = self.upload_file_to_shock('data/Sample5_noninterleaved.1.fastq')
        ref = self.impl.upload_reads(self.ctx, {'fwd_id': ret['id'],
                                                'sequencing_tech': 'seqtech2',
                                                'wsname': self.ws_info[1],
                                                'name': 'singlereads2',
                                                'single_genome': 0})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/singlereads2']})['data'][0]
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech2')
        self.assertEqual(d['single_genome'], 0)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.check_lib(d['lib'], 1116, 'Sample5_noninterleaved.1.fastq',
                       ret['id'], '140a61c7f183dd6a2b93ef195bb3ec63')

        # test saving with IDs only
        ref = self.impl.upload_reads(
            self.ctx, {'fwd_id': ret['id'],
                       'sequencing_tech': 'seqtech2-1',
                       'wsid': self.ws_info[0],
                       'objid': obj['info'][0]})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/singlereads2/2']})['data'][0]
        self.delete_shock_node(ret['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech2-1')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.check_lib(d['lib'], 1116, 'Sample5_noninterleaved.1.fastq',
                       ret['id'], '140a61c7f183dd6a2b93ef195bb3ec63')

    def test_single_end_reads_genome_source_strain(self):
        # specify single genome, source, strain, use workspace id
        ret = self.upload_file_to_shock('data/Sample1.fastq')
        strain = {'genus': 'Yersinia',
                  'species': 'pestis',
                  'strain': 'happypants'
                  }
        source = {'source': 'my pants'}
        ref = self.impl.upload_reads(
            self.ctx,
            {'fwd_id': ret['id'],
             'sequencing_tech': 'seqtech3',
             'wsid': self.ws_info[0],
             'name': 'singlereads3',
             'single_genome': 1,
             'strain': strain,
             'source': source,
             'interleaved': 0
             })
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/singlereads3']})['data'][0]

        self.delete_shock_node(ret['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech3')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual(d['source'], source)
        self.assertEqual(d['strain'], strain)
        self.check_lib(d['lib'], 9648, 'Sample1.fastq', ret['id'],
                       'f118ee769a5e1b40ec44629994dfc3cd')

    def test_paired_end_reads(self):
        # paired end non interlaced, minimum inputs
        ret1 = self.upload_file_to_shock('data/Sample5_noninterleaved.1.fastq')
        ret2 = self.upload_file_to_shock('data/Sample1.fastq.gz')
        ref = self.impl.upload_reads(
            self.ctx, {'fwd_id': ret1['id'],
                       'rev_id': ret2['id'],
                       'sequencing_tech': 'seqtech-pr1',
                       'wsname': self.ws_info[1],
                       'name': 'pairedreads1',
                       'interleaved': 1})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/pairedreads1']})['data'][0]
        self.delete_shock_node(ret1['id'])
        self.delete_shock_node(ret2['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.PairedEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech-pr1')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.assertEqual(d['interleaved'], 0)
        self.assertEqual(d['read_orientation_outward'], 0)
        self.assertEqual(d['insert_size_mean'], None)
        self.assertEqual(d['insert_size_std_dev'], None)
        self.check_lib(d['lib1'], 1116, 'Sample5_noninterleaved.1.fastq',
                       ret1['id'], '140a61c7f183dd6a2b93ef195bb3ec63')
        self.check_lib(d['lib2'], 2847, 'Sample1.fastq.gz',
                       ret2['id'], '48efea6945c4382c68f5eac485c177c2')

    def test_interleaved_with_pe_inputs(self):
        # paired end interlaced with the 4 pe input set
        ret = self.upload_file_to_shock('data/Sample5_interleaved.fastq')
        ref = self.impl.upload_reads(
            self.ctx, {'fwd_id': ret['id'],
                       'sequencing_tech': 'seqtech-pr2',
                       'wsname': self.ws_info[1],
                       'name': 'pairedreads2',
                       'interleaved': 1,
                       'read_orientation_outward': 'a',
                       'insert_size_mean': 72.1,
                       'insert_size_std_dev': 84.0
                       })
        obj = self.ws.get_objects2(
            {'objects': [{'ref': self.ws_info[1] + '/pairedreads2'}]}
            )['data'][0]
        self.delete_shock_node(ret['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.PairedEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech-pr2')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.assertEqual(d['interleaved'], 1)
        self.assertEqual(d['read_orientation_outward'], 1)
        self.assertEqual(d['insert_size_mean'], 72.1)
        self.assertEqual(d['insert_size_std_dev'], 84.0)
        self.check_lib(d['lib1'], 2232, 'Sample5_interleaved.fastq',
                       ret['id'], '971a5f445055c85fd45b17459e15e3ed')

    def check_lib(self, lib, size, filename, id_, md5):
        self.assertEqual(lib['size'], size)
        self.assertEqual(lib['type'], 'fq')
        self.assertEqual(lib['encoding'], 'ascii')
        libfile = lib['file']
        self.assertEqual(libfile['file_name'], filename)
        self.assertEqual(libfile['id'], id_)
        self.assertEqual(libfile['hid'].startswith('KBH_'), True)
        self.assertEqual(libfile['remote_md5'], md5)
        self.assertEqual(libfile['type'], 'shock')
        self.assertEqual(libfile['url'], self.shockURL)

    def fail_upload_reads(self, params, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.upload_reads(self.ctx, params)
        self.assertEqual(error, str(context.exception.message))

    def test_upload_fail_no_reads(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'name': 'foo'
             },
            'No reads file provided')

    def test_upload_fail_no_seqtech(self):
        self.fail_upload_reads(
            {'fwd_id': 'foo',
             'wsname': self.ws_info[1],
             'name': 'foo'
             },
            'The sequencing technology must be provided')

    def test_upload_fail_no_ws(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'fwd_id': 'bar',
             'name': 'foo'
             },
            'Exactly one of the workspace ID or name must be provided')

    def test_upload_fail_no_obj_id(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'fwd_id': 'bar',
             'wsname': self.ws_info[1],
             },
            'Exactly one of the object ID or name must be provided')

    def test_upload_fail_non_existant_objid(self):
        ret = self.upload_file_to_shock('data/Sample1.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret['id'],
             'objid': 1000000
             },
            'There is no object with id 1000000', exception=DFUError)
        self.delete_shock_node(ret['id'])

    def test_upload_fail_non_existant_shockid(self):
        ret = self.upload_file_to_shock('data/Sample1.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'foo',
             'name': 'bar'
             },
            'Error downloading file from shock node foo: Node not found',
            exception=DFUError)
        self.delete_shock_node(ret['id'])

    def test_upload_fail_non_string_wsname(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': 1,
             'fwd_id': 'bar',
             'name': 'foo'
             },
            'wsname must be a string')

    def test_upload_fail_bad_wsname(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': '&bad',
             'fwd_id': 'bar',
             'name': 'foo'
             },
            'Illegal character in workspace name &bad: &', exception=DFUError)

    def test_upload_fail_non_num_mean(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'bar',
             'name': 'foo',
             'insert_size_mean': 'foo'
             },
            'insert_size_mean must be a number')

    def test_upload_fail_non_num_std(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'bar',
             'name': 'foo',
             'insert_size_std_dev': 'foo'
             },
            'insert_size_std_dev must be a number')

    def test_upload_fail_neg_mean(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'bar',
             'name': 'foo',
             'insert_size_mean': 0
             },
            'insert_size_mean must be > 0')

    def test_upload_fail_neg_std(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'bar',
             'name': 'foo',
             'insert_size_std_dev': 0
             },
            'insert_size_std_dev must be > 0')

    def test_upload_fail_bad_fasta(self):
        print('*** upload_fail_bad_fasta ***')
        ret = self.upload_file_to_shock('data/Sample1_invalid.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret['id'],
             'name': 'bar'
             },
            'Invalid fasta file /kb/module/work/tmp/fwd/Sample1_invalid' +
            '.fastq from Shock node ' + ret['id'])
        self.delete_shock_node(ret['id'])

    def test_upload_fail_interleaved_for_single(self):
        ret = self.upload_file_to_shock('data/Sample5_interleaved.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret['id'],
             'name': 'bar'
             },
            'Invalid fasta file /kb/module/work/tmp/fwd/Sample5_interleaved' +
            '.fastq from Shock node ' + ret['id'])
        self.delete_shock_node(ret['id'])

    def test_upload_fail_interleaved_for_paired(self):
        ret1 = self.upload_file_to_shock('data/Sample1.fastq')
        ret2 = self.upload_file_to_shock('data/Sample5_interleaved.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret1['id'],
             'rev_id': ret2['id'],
             'name': 'bar'
             },
            'Invalid fasta file /kb/module/work/tmp/rev/Sample5_interleaved' +
            '.fastq from Shock node ' + ret2['id'])
        self.delete_shock_node(ret1['id'])
        self.delete_shock_node(ret2['id'])

    # Download tests ########################################################

    def test_download_one(self):
        self.download_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                }
             }
        )

    def test_multiple(self):
        self.download_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'intbasic': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                }
             }
        )

    def test_single_end(self):
        self.download_success(
            {'single_end': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'fwd': self.MD5_SM_R},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.reverse.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.forward.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_R},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.reverse.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }
        )

    def test_paired(self):
        self.download_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq.gz',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq.gz'
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                }
             }
        )

    def test_interleaved(self):
        self.download_success(
            {'intbasic': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                }
             }, interleave='none'
        )

    # test some compressed, some uncompressed
    def test_fr_to_interleave(self):
        self.download_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_FR_TO_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq',
                               'rev': None
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_FR_TO_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'interleaved',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq.gz',
                               'rev': None
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_R},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.reverse.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }, interleave='true'
        )

    def download_success(self, testspecs, interleave=None):
        self.maxDiff = None
        test_name = inspect.stack()[1][3]
        print('\n**** starting expected success test: ' + test_name + ' ***\n')

        params = {'read_libraries':
                  [(self.getWsName() + '/' + f) for f in testspecs]
                  }
        if interleave != 'none':
            params['interleaved'] = interleave

        print('Running test with {} libs. Params:'.format(len(testspecs)))
        pprint(params)

        ret = self.impl.download_reads(self.ctx, params)[0]
        print('\n== converter returned:')
        pprint(ret)
        retmap = ret['files']
        self.assertEqual(len(retmap), len(testspecs))
        for f in testspecs:
            wsref = self.getWsName() + '/' + f
            print('== checking testspec ' + f)
            for dirc in testspecs[f]['md5']:
                print('\t== checking md5s for read set ' + dirc)
                expectedmd5 = testspecs[f]['md5'][dirc]
                file_ = retmap[wsref]['files'][dirc]
                fileext = testspecs[f]['fileext'][dirc]
                if not file_.endswith('.' + fileext + '.fastq'):
                    raise TestError('Expected file {} to end with .{}.fastq'
                                    .format(file_, fileext))
                self.assertEqual(expectedmd5, self.md5(file_))
                del retmap[wsref]['files'][dirc]
            self.assertDictEqual(testspecs[f]['obj'], retmap[wsref])
