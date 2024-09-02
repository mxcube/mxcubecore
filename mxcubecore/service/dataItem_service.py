from mxcubecore.utils.pymysql_comm import UsingMysql
from mxcubecore.utils.db import get_db_connection
import logging

AUTOPROC_QUEUE_ID = "autoprocess_queue_id"
XIA2_DIALS_QUEUE_ID = "xia2_dials_queue_id"
XIA2_XDS_QUEUE_ID = "xia2_XDS_queue_id"
AUTOPX_QUEUE_ID = "autopx_queue_id"


def insert_new_data_to_job(frame_number,path,dest,completiontime,status,uuid):
    try:
        with UsingMysql(log_time=True) as um:

            sql = "INSERT INTO job (nimage, src, dest, createtime, status, uuid ) VALUES (%d, '%s', '%s', '%s', '%s', '%s')" % (
                frame_number, path, path, completiontime, status, uuid)
            um.cursor.execute(sql)
            result = um.cursor.fetchall()
            logging.getLogger("HWR").debug("[updateJobStatus from LNLSPilatusDet.py] connect to mysql and result: %s",
                                           result)





    except Exception as ex:
        logging.getLogger("HWR").error("[COLLECT] Data collection job update failure: %s", ex)

def get_queue_id(name:str):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # 下面这样不行，%s只能用于参数
            # sql = "select max(%s) as max_id from job"
            # cursor.execute(sql,(name))

            sql = f"select max({name}) as max_id from job"
            cursor.execute(sql)
            result = cursor.fetchall()

            # for row in result:
            #     print(row[0])

            return result[0][0]+1 if result[0][0] is not None else 1
    finally:
        connection.close()




def insert_new_data_to_all_table(src, dest, status, sample_name, uuid, ion_chamber_intensity, start_angle,
                                 resolution, exposure, image_count, wavelength, distance, oscil_range, beam_x,
                                 beam_y):
    """
    当有新数据时插入各初始参数到所有表
    :param src:
    :param dest:
    :param status:
    :param sample_name:
    :param uuid:
    :param ion_chamber_intensity:
    :param start_angle:
    :param resolution:
    :param exposure:
    :param image_count:
    :param wavelength:
    :param distance:
    :param oscil_range:
    :param beam_x:
    :param beam_y:
    :return:
    """

    autoprocess_queue_id = get_queue_id(AUTOPROC_QUEUE_ID)
    xia2_dials_queue_id = get_queue_id(XIA2_DIALS_QUEUE_ID)
    xia2_xds_queue_id = get_queue_id(XIA2_XDS_QUEUE_ID)
    autopx_queue_id = get_queue_id(AUTOPX_QUEUE_ID)

    # print(src,dest,sample_name,uuid,status,autoprocess_queue_id,xia2_dials_queue_id,xia2_xds_queue_id,autopx_queue_id )
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # 插入job表
            sql_job = f"INSERT INTO Job (src, dest,sample_name,uuid,status, {AUTOPROC_QUEUE_ID},{XIA2_DIALS_QUEUE_ID},{XIA2_XDS_QUEUE_ID},{AUTOPX_QUEUE_ID}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql_job, (
            src, dest, sample_name, uuid, status, autoprocess_queue_id, xia2_dials_queue_id, xia2_xds_queue_id,
            autopx_queue_id))

            job_id = cursor.lastrowid

            # 插入 crystallography_data_basic 表
            sql_collect_parameter = "insert into crystallography_data_basic (job_id, ion_chamber_intensity,start_angle,resolution,exposure,image_count,wavelength,uuid,distance,oscil_range) " \
                                    "Values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql_collect_parameter, (
            job_id, ion_chamber_intensity, start_angle, resolution, exposure, image_count, wavelength, uuid,
            distance, oscil_range))

            # 插入 rawImages 表
            sql_rawImages = "insert into rawImages (job_id,uuid) values (%s,%s)"
            cursor.execute(sql_rawImages, (job_id, uuid))

            # 插入 beam_origin 表
            sql_beam_origin = "insert into beam_origin (job_id,beam_x,beam_y,distance) values (%s,%s,%s,%s)"
            cursor.execute(sql_beam_origin, (job_id, beam_x, beam_y, distance))

            # 插入 autoproc 表
            sql_autoproc = "insert into autoproc (job_id,uuid) values (%s,%s)"
            cursor.execute(sql_autoproc, (job_id, uuid))

            # 插入 xia2_dials 表
            sql_xia2_dials = "insert into xia2_dials (job_id,uuid) values (%s,%s)"
            cursor.execute(sql_xia2_dials, (job_id, uuid))

            # 插入 xia2_xds 表
            sql_xia2_xds = "insert into xia2_xds (job_id,uuid) values (%s,%s)"
            cursor.execute(sql_xia2_xds, (job_id, uuid))

            # 插入 autopx 表
            sql_autopx = "insert into autopx (job_id,uuid) values (%s,%s)"
            cursor.execute(sql_autopx, (job_id, uuid))

            connection.commit()
    except Exception as e:
        connection.rollback()
        print(f" error occurred when insert new data: {e}")
    finally:
        connection.close()


