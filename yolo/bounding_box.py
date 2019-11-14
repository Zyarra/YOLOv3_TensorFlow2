import tensorflow as tf
from configuration import ANCHOR_NUM_EACH_SCALE, CATEGORY_NUM, IMAGE_HEIGHT
from yolo.anchor import get_coco_anchors

# def get_coco_anchors(scale_type):
#     index_list = COCO_ANCHOR_INDEX[scale_type]
#     return tf.convert_to_tensor(COCO_ANCHORS[index_list[0]: index_list[-1] + 1], dtype=tf.dtypes.float32)


def generate_grid_index(grid_dim):
    x = tf.range(grid_dim, dtype=tf.dtypes.float32)
    y = tf.range(grid_dim, dtype=tf.dtypes.float32)
    X, Y = tf.meshgrid(x, y)
    X = tf.reshape(X, shape=(-1, 1))
    Y = tf.reshape(Y, shape=(-1, 1))
    return tf.concat(values=[X, Y], axis=-1)


def bounding_box_predict(feature_map, scale_type, is_training=False):
    h = feature_map.shape[1]
    w = feature_map.shape[2]
    if h != w:
        raise ValueError("The shape[1] and shape[2] of feature map must be the same value.")
    downsampling_rate = IMAGE_HEIGHT // h
    area = h * w
    pred = tf.reshape(feature_map, shape=(-1, ANCHOR_NUM_EACH_SCALE * area, CATEGORY_NUM + 5))
    pred = tf.nn.sigmoid(pred)
    tx_ty, tw_th, confidence, class_prob = tf.split(pred, num_or_size_splits=[2, 2, 1, CATEGORY_NUM], axis=-1)
    center_index = generate_grid_index(grid_dim=h)
    center_index = tf.tile(center_index, [1, ANCHOR_NUM_EACH_SCALE])
    center_index = tf.reshape(center_index, shape=(1, -1, 2))
    # shape : (1, 507, 2), (1, 2028, 2), (1, 8112, 2)

    center_coord = center_index + tx_ty
    anchors = tf.tile(get_coco_anchors(scale_type) / downsampling_rate, [area, 1])
    bw_bh = tf.math.exp(tw_th) * anchors

    box_xy = center_coord * downsampling_rate
    box_wh = bw_bh * downsampling_rate

    # reshape
    center_index = tf.reshape(center_index, shape=(-1, h, w, 3, 2))
    box_xy = tf.reshape(box_xy, shape=(-1, h, w, 3, 2))
    box_wh = tf.reshape(box_wh, shape=(-1, h, w, 3, 2))
    feature_map = tf.reshape(feature_map, shape=(-1, h, w, 3, CATEGORY_NUM + 5))

    # cast dtype
    center_index = tf.cast(center_index, dtype=tf.dtypes.float32)
    box_xy = tf.cast(box_xy, dtype=tf.dtypes.float32)
    box_wh = tf.cast(box_wh, dtype=tf.dtypes.float32)

    # predictions = tf.concat(values=[box_xy,
    #                                 box_wh,
    #                                 confidence,
    #                                 classes],
    #                         axis=-1)
    if is_training:
        return box_xy, box_wh, center_index, feature_map
    else:
        return box_xy, box_wh, confidence, class_prob