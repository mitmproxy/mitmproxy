# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import array
import struct
import zlib
from enum import Enum
from pkg_resources import parse_version

from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO


if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))

class ExifBe(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self.version = self._io.read_u2be()
        self.ifd0_ofs = self._io.read_u4be()

    class Ifd(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.num_fields = self._io.read_u2be()
            self.fields = [None] * (self.num_fields)
            for i in range(self.num_fields):
                self.fields[i] = self._root.IfdField(self._io, self, self._root)

            self.next_ifd_ofs = self._io.read_u4be()

        @property
        def next_ifd(self):
            if hasattr(self, '_m_next_ifd'):
                return self._m_next_ifd if hasattr(self, '_m_next_ifd') else None

            if self.next_ifd_ofs != 0:
                _pos = self._io.pos()
                self._io.seek(self.next_ifd_ofs)
                self._m_next_ifd = self._root.Ifd(self._io, self, self._root)
                self._io.seek(_pos)

            return self._m_next_ifd if hasattr(self, '_m_next_ifd') else None


    class IfdField(KaitaiStruct):

        class FieldTypeEnum(Enum):
            byte = 1
            ascii_string = 2
            word = 3
            dword = 4
            rational = 5

        class TagEnum(Enum):
            image_width = 256
            image_height = 257
            bits_per_sample = 258
            compression = 259
            photometric_interpretation = 262
            thresholding = 263
            cell_width = 264
            cell_length = 265
            fill_order = 266
            document_name = 269
            image_description = 270
            make = 271
            model = 272
            strip_offsets = 273
            orientation = 274
            samples_per_pixel = 277
            rows_per_strip = 278
            strip_byte_counts = 279
            min_sample_value = 280
            max_sample_value = 281
            x_resolution = 282
            y_resolution = 283
            planar_configuration = 284
            page_name = 285
            x_position = 286
            y_position = 287
            free_offsets = 288
            free_byte_counts = 289
            gray_response_unit = 290
            gray_response_curve = 291
            t4_options = 292
            t6_options = 293
            resolution_unit = 296
            page_number = 297
            color_response_unit = 300
            transfer_function = 301
            software = 305
            modify_date = 306
            artist = 315
            host_computer = 316
            predictor = 317
            white_point = 318
            primary_chromaticities = 319
            color_map = 320
            halftone_hints = 321
            tile_width = 322
            tile_length = 323
            tile_offsets = 324
            tile_byte_counts = 325
            bad_fax_lines = 326
            clean_fax_data = 327
            consecutive_bad_fax_lines = 328
            sub_ifd = 330
            ink_set = 332
            ink_names = 333
            numberof_inks = 334
            dot_range = 336
            target_printer = 337
            extra_samples = 338
            sample_format = 339
            s_min_sample_value = 340
            s_max_sample_value = 341
            transfer_range = 342
            clip_path = 343
            x_clip_path_units = 344
            y_clip_path_units = 345
            indexed = 346
            jpeg_tables = 347
            opi_proxy = 351
            global_parameters_ifd = 400
            profile_type = 401
            fax_profile = 402
            coding_methods = 403
            version_year = 404
            mode_number = 405
            decode = 433
            default_image_color = 434
            t82_options = 435
            jpeg_tables2 = 437
            jpeg_proc = 512
            thumbnail_offset = 513
            thumbnail_length = 514
            jpeg_restart_interval = 515
            jpeg_lossless_predictors = 517
            jpeg_point_transforms = 518
            jpegq_tables = 519
            jpegdc_tables = 520
            jpegac_tables = 521
            y_cb_cr_coefficients = 529
            y_cb_cr_sub_sampling = 530
            y_cb_cr_positioning = 531
            reference_black_white = 532
            strip_row_counts = 559
            application_notes = 700
            uspto_miscellaneous = 999
            related_image_file_format = 4096
            related_image_width = 4097
            related_image_height = 4098
            rating = 18246
            xp_dip_xml = 18247
            stitch_info = 18248
            rating_percent = 18249
            sony_raw_file_type = 28672
            light_falloff_params = 28722
            chromatic_aberration_corr_params = 28725
            distortion_corr_params = 28727
            image_id = 32781
            wang_tag1 = 32931
            wang_annotation = 32932
            wang_tag3 = 32933
            wang_tag4 = 32934
            image_reference_points = 32953
            region_xform_tack_point = 32954
            warp_quadrilateral = 32955
            affine_transform_mat = 32956
            matteing = 32995
            data_type = 32996
            image_depth = 32997
            tile_depth = 32998
            image_full_width = 33300
            image_full_height = 33301
            texture_format = 33302
            wrap_modes = 33303
            fov_cot = 33304
            matrix_world_to_screen = 33305
            matrix_world_to_camera = 33306
            model2 = 33405
            cfa_repeat_pattern_dim = 33421
            cfa_pattern2 = 33422
            battery_level = 33423
            kodak_ifd = 33424
            copyright = 33432
            exposure_time = 33434
            f_number = 33437
            md_file_tag = 33445
            md_scale_pixel = 33446
            md_color_table = 33447
            md_lab_name = 33448
            md_sample_info = 33449
            md_prep_date = 33450
            md_prep_time = 33451
            md_file_units = 33452
            pixel_scale = 33550
            advent_scale = 33589
            advent_revision = 33590
            uic1_tag = 33628
            uic2_tag = 33629
            uic3_tag = 33630
            uic4_tag = 33631
            iptc_naa = 33723
            intergraph_packet_data = 33918
            intergraph_flag_registers = 33919
            intergraph_matrix = 33920
            ingr_reserved = 33921
            model_tie_point = 33922
            site = 34016
            color_sequence = 34017
            it8_header = 34018
            raster_padding = 34019
            bits_per_run_length = 34020
            bits_per_extended_run_length = 34021
            color_table = 34022
            image_color_indicator = 34023
            background_color_indicator = 34024
            image_color_value = 34025
            background_color_value = 34026
            pixel_intensity_range = 34027
            transparency_indicator = 34028
            color_characterization = 34029
            hc_usage = 34030
            trap_indicator = 34031
            cmyk_equivalent = 34032
            sem_info = 34118
            afcp_iptc = 34152
            pixel_magic_jbig_options = 34232
            jpl_carto_ifd = 34263
            model_transform = 34264
            wb_grgb_levels = 34306
            leaf_data = 34310
            photoshop_settings = 34377
            exif_offset = 34665
            icc_profile = 34675
            tiff_fx_extensions = 34687
            multi_profiles = 34688
            shared_data = 34689
            t88_options = 34690
            image_layer = 34732
            geo_tiff_directory = 34735
            geo_tiff_double_params = 34736
            geo_tiff_ascii_params = 34737
            jbig_options = 34750
            exposure_program = 34850
            spectral_sensitivity = 34852
            gps_info = 34853
            iso = 34855
            opto_electric_conv_factor = 34856
            interlace = 34857
            time_zone_offset = 34858
            self_timer_mode = 34859
            sensitivity_type = 34864
            standard_output_sensitivity = 34865
            recommended_exposure_index = 34866
            iso_speed = 34867
            iso_speed_latitudeyyy = 34868
            iso_speed_latitudezzz = 34869
            fax_recv_params = 34908
            fax_sub_address = 34909
            fax_recv_time = 34910
            fedex_edr = 34929
            leaf_sub_ifd = 34954
            exif_version = 36864
            date_time_original = 36867
            create_date = 36868
            google_plus_upload_code = 36873
            offset_time = 36880
            offset_time_original = 36881
            offset_time_digitized = 36882
            components_configuration = 37121
            compressed_bits_per_pixel = 37122
            shutter_speed_value = 37377
            aperture_value = 37378
            brightness_value = 37379
            exposure_compensation = 37380
            max_aperture_value = 37381
            subject_distance = 37382
            metering_mode = 37383
            light_source = 37384
            flash = 37385
            focal_length = 37386
            flash_energy = 37387
            spatial_frequency_response = 37388
            noise = 37389
            focal_plane_x_resolution = 37390
            focal_plane_y_resolution = 37391
            focal_plane_resolution_unit = 37392
            image_number = 37393
            security_classification = 37394
            image_history = 37395
            subject_area = 37396
            exposure_index = 37397
            tiff_ep_standard_id = 37398
            sensing_method = 37399
            cip3_data_file = 37434
            cip3_sheet = 37435
            cip3_side = 37436
            sto_nits = 37439
            maker_note = 37500
            user_comment = 37510
            sub_sec_time = 37520
            sub_sec_time_original = 37521
            sub_sec_time_digitized = 37522
            ms_document_text = 37679
            ms_property_set_storage = 37680
            ms_document_text_position = 37681
            image_source_data = 37724
            ambient_temperature = 37888
            humidity = 37889
            pressure = 37890
            water_depth = 37891
            acceleration = 37892
            camera_elevation_angle = 37893
            xp_title = 40091
            xp_comment = 40092
            xp_author = 40093
            xp_keywords = 40094
            xp_subject = 40095
            flashpix_version = 40960
            color_space = 40961
            exif_image_width = 40962
            exif_image_height = 40963
            related_sound_file = 40964
            interop_offset = 40965
            samsung_raw_pointers_offset = 40976
            samsung_raw_pointers_length = 40977
            samsung_raw_byte_order = 41217
            samsung_raw_unknown = 41218
            flash_energy2 = 41483
            spatial_frequency_response2 = 41484
            noise2 = 41485
            focal_plane_x_resolution2 = 41486
            focal_plane_y_resolution2 = 41487
            focal_plane_resolution_unit2 = 41488
            image_number2 = 41489
            security_classification2 = 41490
            image_history2 = 41491
            subject_location = 41492
            exposure_index2 = 41493
            tiff_ep_standard_id2 = 41494
            sensing_method2 = 41495
            file_source = 41728
            scene_type = 41729
            cfa_pattern = 41730
            custom_rendered = 41985
            exposure_mode = 41986
            white_balance = 41987
            digital_zoom_ratio = 41988
            focal_length_in35mm_format = 41989
            scene_capture_type = 41990
            gain_control = 41991
            contrast = 41992
            saturation = 41993
            sharpness = 41994
            device_setting_description = 41995
            subject_distance_range = 41996
            image_unique_id = 42016
            owner_name = 42032
            serial_number = 42033
            lens_info = 42034
            lens_make = 42035
            lens_model = 42036
            lens_serial_number = 42037
            gdal_metadata = 42112
            gdal_no_data = 42113
            gamma = 42240
            expand_software = 44992
            expand_lens = 44993
            expand_film = 44994
            expand_filter_lens = 44995
            expand_scanner = 44996
            expand_flash_lamp = 44997
            pixel_format = 48129
            transformation = 48130
            uncompressed = 48131
            image_type = 48132
            image_width2 = 48256
            image_height2 = 48257
            width_resolution = 48258
            height_resolution = 48259
            image_offset = 48320
            image_byte_count = 48321
            alpha_offset = 48322
            alpha_byte_count = 48323
            image_data_discard = 48324
            alpha_data_discard = 48325
            oce_scanjob_desc = 50215
            oce_application_selector = 50216
            oce_id_number = 50217
            oce_image_logic = 50218
            annotations = 50255
            print_im = 50341
            original_file_name = 50547
            uspto_original_content_type = 50560
            dng_version = 50706
            dng_backward_version = 50707
            unique_camera_model = 50708
            localized_camera_model = 50709
            cfa_plane_color = 50710
            cfa_layout = 50711
            linearization_table = 50712
            black_level_repeat_dim = 50713
            black_level = 50714
            black_level_delta_h = 50715
            black_level_delta_v = 50716
            white_level = 50717
            default_scale = 50718
            default_crop_origin = 50719
            default_crop_size = 50720
            color_matrix1 = 50721
            color_matrix2 = 50722
            camera_calibration1 = 50723
            camera_calibration2 = 50724
            reduction_matrix1 = 50725
            reduction_matrix2 = 50726
            analog_balance = 50727
            as_shot_neutral = 50728
            as_shot_white_xy = 50729
            baseline_exposure = 50730
            baseline_noise = 50731
            baseline_sharpness = 50732
            bayer_green_split = 50733
            linear_response_limit = 50734
            camera_serial_number = 50735
            dng_lens_info = 50736
            chroma_blur_radius = 50737
            anti_alias_strength = 50738
            shadow_scale = 50739
            sr2_private = 50740
            maker_note_safety = 50741
            raw_image_segmentation = 50752
            calibration_illuminant1 = 50778
            calibration_illuminant2 = 50779
            best_quality_scale = 50780
            raw_data_unique_id = 50781
            alias_layer_metadata = 50784
            original_raw_file_name = 50827
            original_raw_file_data = 50828
            active_area = 50829
            masked_areas = 50830
            as_shot_icc_profile = 50831
            as_shot_pre_profile_matrix = 50832
            current_icc_profile = 50833
            current_pre_profile_matrix = 50834
            colorimetric_reference = 50879
            s_raw_type = 50885
            panasonic_title = 50898
            panasonic_title2 = 50899
            camera_calibration_sig = 50931
            profile_calibration_sig = 50932
            profile_ifd = 50933
            as_shot_profile_name = 50934
            noise_reduction_applied = 50935
            profile_name = 50936
            profile_hue_sat_map_dims = 50937
            profile_hue_sat_map_data1 = 50938
            profile_hue_sat_map_data2 = 50939
            profile_tone_curve = 50940
            profile_embed_policy = 50941
            profile_copyright = 50942
            forward_matrix1 = 50964
            forward_matrix2 = 50965
            preview_application_name = 50966
            preview_application_version = 50967
            preview_settings_name = 50968
            preview_settings_digest = 50969
            preview_color_space = 50970
            preview_date_time = 50971
            raw_image_digest = 50972
            original_raw_file_digest = 50973
            sub_tile_block_size = 50974
            row_interleave_factor = 50975
            profile_look_table_dims = 50981
            profile_look_table_data = 50982
            opcode_list1 = 51008
            opcode_list2 = 51009
            opcode_list3 = 51022
            noise_profile = 51041
            time_codes = 51043
            frame_rate = 51044
            t_stop = 51058
            reel_name = 51081
            original_default_final_size = 51089
            original_best_quality_size = 51090
            original_default_crop_size = 51091
            camera_label = 51105
            profile_hue_sat_map_encoding = 51107
            profile_look_table_encoding = 51108
            baseline_exposure_offset = 51109
            default_black_render = 51110
            new_raw_image_digest = 51111
            raw_to_preview_gain = 51112
            default_user_crop = 51125
            padding = 59932
            offset_schema = 59933
            owner_name2 = 65000
            serial_number2 = 65001
            lens = 65002
            kdc_ifd = 65024
            raw_file = 65100
            converter = 65101
            white_balance2 = 65102
            exposure = 65105
            shadows = 65106
            brightness = 65107
            contrast2 = 65108
            saturation2 = 65109
            sharpness2 = 65110
            smoothness = 65111
            moire_filter = 65112
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.tag = self._root.IfdField.TagEnum(self._io.read_u2be())
            self.field_type = self._root.IfdField.FieldTypeEnum(self._io.read_u2be())
            self.length = self._io.read_u4be()
            self.ofs_or_data = self._io.read_u4be()

        @property
        def type_byte_length(self):
            if hasattr(self, '_m_type_byte_length'):
                return self._m_type_byte_length if hasattr(self, '_m_type_byte_length') else None

            self._m_type_byte_length = (2 if self.field_type == self._root.IfdField.FieldTypeEnum.word else (4 if self.field_type == self._root.IfdField.FieldTypeEnum.dword else 1))
            return self._m_type_byte_length if hasattr(self, '_m_type_byte_length') else None

        @property
        def byte_length(self):
            if hasattr(self, '_m_byte_length'):
                return self._m_byte_length if hasattr(self, '_m_byte_length') else None

            self._m_byte_length = (self.length * self.type_byte_length)
            return self._m_byte_length if hasattr(self, '_m_byte_length') else None

        @property
        def is_immediate_data(self):
            if hasattr(self, '_m_is_immediate_data'):
                return self._m_is_immediate_data if hasattr(self, '_m_is_immediate_data') else None

            self._m_is_immediate_data = self.byte_length <= 4
            return self._m_is_immediate_data if hasattr(self, '_m_is_immediate_data') else None

        @property
        def data(self):
            if hasattr(self, '_m_data'):
                return self._m_data if hasattr(self, '_m_data') else None

            if not self.is_immediate_data:
                io = self._root._io
                _pos = io.pos()
                io.seek(self.ofs_or_data)
                self._m_data = io.read_bytes(self.byte_length)
                io.seek(_pos)

            return self._m_data if hasattr(self, '_m_data') else None


    @property
    def ifd0(self):
        if hasattr(self, '_m_ifd0'):
            return self._m_ifd0 if hasattr(self, '_m_ifd0') else None

        _pos = self._io.pos()
        self._io.seek(self.ifd0_ofs)
        self._m_ifd0 = self._root.Ifd(self._io, self, self._root)
        self._io.seek(_pos)
        return self._m_ifd0 if hasattr(self, '_m_ifd0') else None


