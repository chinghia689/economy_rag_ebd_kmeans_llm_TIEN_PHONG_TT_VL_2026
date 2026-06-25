import type { PublicContentData } from '../types';

export const DEFAULT_PUBLIC_CONTENT: PublicContentData = {
  privacy: {
    title: 'Chính sách bảo mật',
    content: 'Thông tin về cách hệ thống thu thập, sử dụng và bảo vệ dữ liệu tài khoản đang được cập nhật.',
  },
  terms: {
    title: 'Điều khoản sử dụng',
    content: 'Điều khoản sử dụng dịch vụ đang được cập nhật.',
  },
  support: {
    title: 'Hỗ trợ',
    content: 'Nếu gặp vấn đề khi sử dụng dịch vụ, vui lòng liên hệ quản trị viên để được hỗ trợ.',
    email: '',
  },
};
