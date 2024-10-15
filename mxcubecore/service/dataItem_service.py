from mxcubecore.utils.pymysql_comm import UsingMysql
from mxcubecore.utils.db import get_db_connection
import logging
from datetime import datetime


AUTOPROC_QUEUE_ID = "autoprocess_queue_id"
XIA2_DIALS_QUEUE_ID = "xia2_dials_queue_id"
XIA2_XDS_QUEUE_ID = "xia2_xds_queue_id"
AUTOPX_QUEUE_ID = "autopx_queue_id"


def insert_new_data_to_job(frame_number,path,dest,completiontime,status,uuid,filename):
    job_id = ""
    try:
        with UsingMysql(log_time=True) as um:

            sql = "INSERT INTO job (nimage, src, dest, createtime, status, uuid ,sample_name) VALUES (%d, '%s', '%s', '%s', '%s', '%s', '%s')" % (
                frame_number, path, dest, completiontime, status, uuid, filename)
            um.cursor.execute(sql)
            job_id = um.cursor.lastrowid
            logging.getLogger("HWR").debug("[insert_new_data_to_job from dataItem_service.py] connect to mysql succeeded, job_id = %s",job_id)

    except Exception as ex:
        logging.getLogger("HWR").error("[insert_new_data_to_job from dataItem_service.py] Data collection job update failure: %s", ex)
    return job_id


def insert_dc_param_to_basic(job_id,ion_chamber_intensity,start_angle,resolution,exposure,image_count,wavelength,uuid,distance,oscil_range):
    try:
        with UsingMysql(log_time=True) as um:
            sql_collect_parameter = "insert into crystallography_data_basic (job_id,ion_chamber_intensity,start_angle,resolution,exposure,image_count,wavelength,uuid,distance,oscil_range) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            um.cursor.execute(sql_collect_parameter,(job_id, ion_chamber_intensity, start_angle, resolution, exposure, image_count, wavelength, uuid,distance, oscil_range))
            # result = um.cursor.fetchall()
            logging.getLogger("HWR").debug("[insert_dc_param_to_basic from dataItem_service.py] connect to mysql succeeded")
    except Exception as ex:
        logging.getLogger("HWR").error("[insert_dc_param_to_basic from dataItem_service.py] insert_dc_param_to_basic failure: %s", ex)


def get_queue_id(name:str):
    try:
        with UsingMysql(log_time=True) as um:
            # 下面这样不行，%s只能用于参数
            # sql = "select max(%s) as max_id from job"
            # cursor.execute(sql,(name))

            sql = f"select max({name}) as max_id from job"
            um.cursor.execute(sql)
            result = um.cursor.fetchall()
            # print(result[0]['max_id'],type(result),result)  # dict cursor
            return result[0]['max_id'] + 1 if result[0]['max_id'] is not None else 1
    except Exception as ex:
        logging.getLogger("HWR").error(f"[get_queue_id from dataItem_service.py] get {name} failure: {ex}")
        raise






def updateRawImagesSnapshot(job_id,snapReady,snapUrl):
    try:
        with UsingMysql(log_time=True) as um:
            sql = "update rawImages set snapReady = '%s',snapUrl = '%s' where job_id = '%s'" % (snapReady,snapUrl,job_id)
            um.cursor.execute(sql)
            # result = um.cursor.fetchall()
            logging.getLogger("HWR").debug("[updateRawImagesSnapshot from dataItem_service.py] connect to mysql succeeded")
            logging.getLogger("HWR").debug(sql)
    except Exception as ex:
        logging.getLogger("HWR").error("[updateRawImagesSnapshot from dataItem_service.py] updateRawImagesSnapshot failure: %s", ex)


# after collection finish
def updateJobStatus_when_finished(uuid,status):
    completiontime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with UsingMysql(log_time=True) as um:
        sql = "UPDATE job SET completiontime = '%s', status = '%s'  WHERE uuid = '%s'" % (
        completiontime, status, uuid)
        um.cursor.execute(sql)




# before collection finshed
def updateOtherTable(uuid,job_id,distance):
    with UsingMysql(log_time=True) as um:

        # 插入 rawImages 表
        sql_rawImages = "insert into rawImages (job_id,uuid) values (%s,%s)"
        um.cursor.execute(sql_rawImages, (job_id, uuid))

        # 插入 beam_origin 表
        sql_beam_origin = "insert into beam_origin (job_id,beam_x,beam_y,distance) values (%s,%s,%s,%s)"
        um.cursor.execute(sql_beam_origin, (job_id, None, None, distance))

        # 插入 autoproc 表
        sql_autoproc = "insert into autoproc (job_id,uuid) values (%s,%s)"
        um.cursor.execute(sql_autoproc, (job_id, uuid))

        # 插入 xia2_dials 表
        sql_xia2_dials = "insert into xia2_dials (job_id,uuid) values (%s,%s)"
        um.cursor.execute(sql_xia2_dials, (job_id, uuid))

        # 插入 xia2_xds 表
        sql_xia2_xds = "insert into xia2_xds (job_id,uuid) values (%s,%s)"
        um.cursor.execute(sql_xia2_xds, (job_id, uuid))

        # 插入 autopx 表
        sql_autopx = "insert into autopx (job_id,uuid) values (%s,%s)"
        um.cursor.execute(sql_autopx, (job_id, uuid))








        sql = "select nimage as nimage from job where uuid = '%s'" %(uuid)
        um.cursor.execute(sql)
        nimage = um.cursor.fetchall()
        nimage = nimage[0]['nimage']

        if nimage > 10:
            next_autoproc_queue_id = get_queue_id(AUTOPROC_QUEUE_ID)
            next_xia2_dials_queue_id = get_queue_id(XIA2_DIALS_QUEUE_ID)
            next_xia2_xds_queue_id = get_queue_id(XIA2_XDS_QUEUE_ID)
            next_autopx_queue_id = get_queue_id(AUTOPX_QUEUE_ID)

            logging.getLogger("HWR").debug(
                " [updateOtherTable] next_autopx_queue_id: %d , next_xds_queue_id: %d, next_dials_queue_id: %d, next_autoproc_queue_id: %d",
                next_autopx_queue_id, next_xia2_xds_queue_id, next_xia2_dials_queue_id, next_autoproc_queue_id)
            waiting = "waiting..."

            sql = "UPDATE job SET autopx = '%s', xia2_xds_result = '%s',autoprocess_result = '%s', xia2_dials_result = '%s', autopx_queue_id = %d, xia2_xds_queue_id=%d,xia2_dials_queue_id=%d,autoprocess_queue_id=%d WHERE uuid = '%s'" % (
                waiting, waiting, waiting, waiting, next_autopx_queue_id, next_xia2_xds_queue_id, next_xia2_dials_queue_id,
                next_autoproc_queue_id, uuid)
            um.cursor.execute(sql)

        logging.getLogger("HWR").debug("[updateOtherTable from dataItem_service.py] connect to mysql succeeded")




if __name__ == "__main__":
    # test1
    # dc_basic_data = [75198,None,225.58,2.5,0.1,1,0.979,'c9294',508.9,1]
    # insert_dc_param_to_basic(*dc_basic_data)

    # test2
    get_queue_id(AUTOPROC_QUEUE_ID)