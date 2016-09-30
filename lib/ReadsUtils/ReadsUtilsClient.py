# -*- coding: utf-8 -*-
############################################################
#
# Autogenerated by the KBase type compiler -
# any changes made here will be overwritten
#
############################################################

from __future__ import print_function
# the following is a hack to get the baseclient to import whether we're in a
# package or not. This makes pep8 unhappy hence the annotations.
try:
    # baseclient and this client are in a package
    from .baseclient import BaseClient as _BaseClient  # @UnusedImport
except:
    # no they aren't
    from baseclient import BaseClient as _BaseClient  # @Reimport


class ReadsUtils(object):

    def __init__(
            self, url=None, timeout=30 * 60, user_id=None,
            password=None, token=None, ignore_authrc=False,
            trust_all_ssl_certificates=False,
            auth_svc='https://kbase.us/services/authorization/Sessions/Login'):
        if url is None:
            raise ValueError('A url is required')
        self._service_ver = None
        self._client = _BaseClient(
            url, timeout=timeout, user_id=user_id, password=password,
            token=token, ignore_authrc=ignore_authrc,
            trust_all_ssl_certificates=trust_all_ssl_certificates,
            auth_svc=auth_svc)

    def validateFASTQ(self, params, context=None):
        """
        Validate a FASTQ file. The file extensions .fq, .fnq, and .fastq
        are accepted. Note that prior to validation the file will be altered in
        place to remove blank lines if any exist.
        :param params: instance of list of type "ValidateFASTQParams" (Input
           to the validateFASTQ function. Required parameters: file_path -
           the path to the file to validate. Optional parameters: interleaved
           - whether the file is interleaved or not. Setting this to true
           disables sequence ID checks.) -> structure: parameter "file_path"
           of String, parameter "interleaved" of type "boolean" (A boolean -
           0 for false, 1 for true. @range (0, 1))
        :returns: instance of list of type "ValidateFASTQOutput" (The output
           of the validateFASTQ function. validated - whether the file
           validated successfully or not.) -> structure: parameter
           "validated" of type "boolean" (A boolean - 0 for false, 1 for
           true. @range (0, 1))
        """
        return self._client.call_method(
            'ReadsUtils.validateFASTQ',
            [params], self._service_ver, context)

    def upload_reads(self, params, context=None):
        """
        Loads a set of reads to KBase data stores.
        :param params: instance of type "UploadReadsParams" (Input to the
           upload_reads function. If local files are specified for upload,
           they must be uncompressed. Files will be gzipped prior to upload.
           Note that if a reverse read file is specified, it must be a local
           file if the forward reads file is a local file, or a shock id if
           not. Required parameters: fwd_id - the id of the shock node
           containing the reads data file: either single end reads,
           forward/left reads, or interleaved reads. - OR - fwd_file - a
           local path to the reads data file: either single end reads,
           forward/left reads, or interleaved reads. sequencing_tech - the
           sequencing technology used to produce the reads. One of: wsid -
           the id of the workspace where the reads will be saved (preferred).
           wsname - the name of the workspace where the reads will be saved.
           One of: objid - the id of the workspace object to save over name -
           the name to which the workspace object will be saved Optional
           parameters: rev_id - the shock node id containing the
           reverse/right reads for paired end, non-interleaved reads. - OR -
           rev_file - a local path to the reads data file containing the
           reverse/right reads for paired end, non-interleaved reads.
           single_genome - whether the reads are from a single genome or a
           metagenome. Default is single genome. strain - information about
           the organism strain that was sequenced. source - information about
           the organism source. interleaved - specify that the fwd reads file
           is an interleaved paired end reads file as opposed to a single end
           reads file. Default true, ignored if rev_id is specified.
           read_orientation_outward - whether the read orientation is outward
           from the set of primers. Default is false and is ignored for
           single end reads. insert_size_mean - the mean size of the genetic
           fragments. Ignored for single end reads. insert_size_std_dev - the
           standard deviation of the size of the genetic fragments. Ignored
           for single end reads.) -> structure: parameter "fwd_id" of String,
           parameter "fwd_file" of String, parameter "wsid" of Long,
           parameter "wsname" of String, parameter "objid" of Long, parameter
           "name" of String, parameter "rev_id" of String, parameter
           "rev_file" of String, parameter "sequencing_tech" of String,
           parameter "single_genome" of type "boolean" (A boolean - 0 for
           false, 1 for true. @range (0, 1)), parameter "strain" of type
           "StrainInfo" (Information about a strain. genetic_code - the
           genetic code of the strain. See
           http://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi?mode=c
           genus - the genus of the strain species - the species of the
           strain strain - the identifier for the strain source - information
           about the source of the strain organelle - the organelle of
           interest for the related data (e.g. mitochondria) ncbi_taxid - the
           NCBI taxonomy ID of the strain location - the location from which
           the strain was collected @optional genetic_code source ncbi_taxid
           organelle location) -> structure: parameter "genetic_code" of
           Long, parameter "genus" of String, parameter "species" of String,
           parameter "strain" of String, parameter "organelle" of String,
           parameter "source" of type "SourceInfo" (Information about the
           source of a piece of data. source - the name of the source (e.g.
           NCBI, JGI, Swiss-Prot) source_id - the ID of the data at the
           source project_id - the ID of a project encompassing the data at
           the source @optional source source_id project_id) -> structure:
           parameter "source" of String, parameter "source_id" of type
           "source_id" (An ID used for a piece of data at its source. @id
           external), parameter "project_id" of type "project_id" (An ID used
           for a project encompassing a piece of data at its source. @id
           external), parameter "ncbi_taxid" of Long, parameter "location" of
           type "Location" (Information about a location. lat - latitude of
           the site, recorded as a decimal number. North latitudes are
           positive values and south latitudes are negative numbers. lon -
           longitude of the site, recorded as a decimal number. West
           longitudes are positive values and east longitudes are negative
           numbers. elevation - elevation of the site, expressed in meters
           above sea level. Negative values are allowed. date - date of an
           event at this location (for example, sample collection), expressed
           in the format YYYY-MM-DDThh:mm:ss.SSSZ description - a free text
           description of the location and, if applicable, the associated
           event. @optional date description) -> structure: parameter "lat"
           of Double, parameter "lon" of Double, parameter "elevation" of
           Double, parameter "date" of String, parameter "description" of
           String, parameter "source" of type "SourceInfo" (Information about
           the source of a piece of data. source - the name of the source
           (e.g. NCBI, JGI, Swiss-Prot) source_id - the ID of the data at the
           source project_id - the ID of a project encompassing the data at
           the source @optional source source_id project_id) -> structure:
           parameter "source" of String, parameter "source_id" of type
           "source_id" (An ID used for a piece of data at its source. @id
           external), parameter "project_id" of type "project_id" (An ID used
           for a project encompassing a piece of data at its source. @id
           external), parameter "interleaved" of type "boolean" (A boolean -
           0 for false, 1 for true. @range (0, 1)), parameter
           "read_orientation_outward" of type "boolean" (A boolean - 0 for
           false, 1 for true. @range (0, 1)), parameter "insert_size_mean" of
           Double, parameter "insert_size_std_dev" of Double
        :returns: instance of type "UploadReadsOutput" (The output of the
           upload_reads function. obj_ref - a reference to the new Workspace
           object in the form X/Y/Z, where X is the workspace ID, Y is the
           object ID, and Z is the version.) -> structure: parameter
           "obj_ref" of String
        """
        return self._client.call_method(
            'ReadsUtils.upload_reads',
            [params], self._service_ver, context)

    def download_reads(self, params, context=None):
        """
        Download read libraries. Reads compressed with gzip or bzip are
        automatically uncompressed.
        :param params: instance of type "DownloadReadsParams" (Input
           parameters for downloading reads objects. list<read_lib>
           read_libraries - the the workspace read library objects to
           download. tern interleaved - if true, provide the files in
           interleaved format if they are not already. If false, provide
           forward and reverse reads files. If null or missing, leave files
           as is.) -> structure: parameter "read_libraries" of list of type
           "read_lib" (A reference to a read library stored in the workspace
           service, whether of the KBaseAssembly or KBaseFile type. Usage of
           absolute references (e.g. 256/3/6) is strongly encouraged to avoid
           race conditions, although any valid reference is allowed.),
           parameter "interleaved" of type "tern" (A ternary. Allowed values
           are 'false', 'true', or null. Any other value is invalid.)
        :returns: instance of type "DownloadReadsOutput" (The output of the
           download method. mapping<read_lib, DownloadedReadLibrary> files -
           a mapping of the read library workspace references to information
           about the converted data for each library.) -> structure:
           parameter "files" of mapping from type "read_lib" (A reference to
           a read library stored in the workspace service, whether of the
           KBaseAssembly or KBaseFile type. Usage of absolute references
           (e.g. 256/3/6) is strongly encouraged to avoid race conditions,
           although any valid reference is allowed.) to type
           "DownloadedReadLibrary" (Information about each set of reads.
           ReadsFiles files - the reads files. string ref - the absolute
           workspace reference of the reads file, e.g
           workspace_id/object_id/version. tern single_genome - whether the
           reads are from a single genome or a metagenome. null if unknown.
           tern read_orientation_outward - whether the read orientation is
           outward from the set of primers. null if unknown or single ended
           reads. string sequencing_tech - the sequencing technology used to
           produce the reads. null if unknown. KBaseCommon.StrainInfo strain
           - information about the organism strain that was sequenced. null
           if unavailable. KBaseCommon.SourceInfo source - information about
           the organism source. null if unavailable. float insert_size_mean -
           the mean size of the genetic fragments. null if unavailable or
           single end reads. float insert_size_std_dev - the standard
           deviation of the size of the genetic fragments. null if
           unavailable or single end reads. int read_count - the number of
           reads in the this dataset. null if unavailable. int read_size -
           the total size of the reads, in bases. null if unavailable. float
           gc_content - the GC content of the reads. null if unavailable.) ->
           structure: parameter "files" of type "ReadsFiles" (Reads file
           information. Note that the file names provided are those *prior
           to* interleaving or deinterleaving the reads. string fwd - the
           path to the forward / left reads. string fwd_name - the name of
           the forwards reads file from Shock, or if not available, from the
           Shock handle. string rev - the path to the reverse / right reads.
           null if the reads are single end or interleaved. string rev_name -
           the name of the reverse reads file from Shock, or if not
           available, from the Shock handle. null if the reads are single end
           or interleaved. string otype - the original type of the reads. One
           of 'single', 'paired', or 'interleaved'. string type - one of
           'single', 'paired', or 'interleaved'.) -> structure: parameter
           "fwd" of String, parameter "fwd_name" of String, parameter "rev"
           of String, parameter "rev_name" of String, parameter "otype" of
           String, parameter "type" of String, parameter "ref" of String,
           parameter "single_genome" of type "tern" (A ternary. Allowed
           values are 'false', 'true', or null. Any other value is invalid.),
           parameter "read_orientation_outward" of type "tern" (A ternary.
           Allowed values are 'false', 'true', or null. Any other value is
           invalid.), parameter "sequencing_tech" of String, parameter
           "strain" of type "StrainInfo" (Information about a strain.
           genetic_code - the genetic code of the strain. See
           http://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi?mode=c
           genus - the genus of the strain species - the species of the
           strain strain - the identifier for the strain source - information
           about the source of the strain organelle - the organelle of
           interest for the related data (e.g. mitochondria) ncbi_taxid - the
           NCBI taxonomy ID of the strain location - the location from which
           the strain was collected @optional genetic_code source ncbi_taxid
           organelle location) -> structure: parameter "genetic_code" of
           Long, parameter "genus" of String, parameter "species" of String,
           parameter "strain" of String, parameter "organelle" of String,
           parameter "source" of type "SourceInfo" (Information about the
           source of a piece of data. source - the name of the source (e.g.
           NCBI, JGI, Swiss-Prot) source_id - the ID of the data at the
           source project_id - the ID of a project encompassing the data at
           the source @optional source source_id project_id) -> structure:
           parameter "source" of String, parameter "source_id" of type
           "source_id" (An ID used for a piece of data at its source. @id
           external), parameter "project_id" of type "project_id" (An ID used
           for a project encompassing a piece of data at its source. @id
           external), parameter "ncbi_taxid" of Long, parameter "location" of
           type "Location" (Information about a location. lat - latitude of
           the site, recorded as a decimal number. North latitudes are
           positive values and south latitudes are negative numbers. lon -
           longitude of the site, recorded as a decimal number. West
           longitudes are positive values and east longitudes are negative
           numbers. elevation - elevation of the site, expressed in meters
           above sea level. Negative values are allowed. date - date of an
           event at this location (for example, sample collection), expressed
           in the format YYYY-MM-DDThh:mm:ss.SSSZ description - a free text
           description of the location and, if applicable, the associated
           event. @optional date description) -> structure: parameter "lat"
           of Double, parameter "lon" of Double, parameter "elevation" of
           Double, parameter "date" of String, parameter "description" of
           String, parameter "source" of type "SourceInfo" (Information about
           the source of a piece of data. source - the name of the source
           (e.g. NCBI, JGI, Swiss-Prot) source_id - the ID of the data at the
           source project_id - the ID of a project encompassing the data at
           the source @optional source source_id project_id) -> structure:
           parameter "source" of String, parameter "source_id" of type
           "source_id" (An ID used for a piece of data at its source. @id
           external), parameter "project_id" of type "project_id" (An ID used
           for a project encompassing a piece of data at its source. @id
           external), parameter "insert_size_mean" of Double, parameter
           "insert_size_std_dev" of Double, parameter "read_count" of Long,
           parameter "read_size" of Long, parameter "gc_content" of Double
        """
        return self._client.call_method(
            'ReadsUtils.download_reads',
            [params], self._service_ver, context)

    def status(self, context=None):
        return self._client.call_method('ReadsUtils.status',
                                        [], self._service_ver, context)
